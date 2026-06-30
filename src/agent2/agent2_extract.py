#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent2_extract.py — agent2(AI 분석 엔진) 추출/분류/요약 프로토타입

입력: agent1의 output(mock_agent1_output.json) = agent2의 입력 계약(공고문/RFP 파싱 결과).
처리: 명세서 C(분류)/D(핵심항목 추출, tool use 고정 스키마)/E(요약).
출력: agent3 대시보드가 소비하는 단일 JSON(agent2_output.json) + 데모용 HTML(preview.html).

모드:
  - LIVE  : ANTHROPIC_API_KEY + anthropic SDK 있으면 Claude tool use 강제 호출.
  - OFFLINE: 키/SDK 없으면 규칙 기반으로 동일 스키마를 채워 파이프라인·검증을 그대로 검증.

실행: python3 agent2_extract.py
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).parent
MOCK = HERE / "mock_agent1_output.json"
OUT_JSON = HERE / "agent2_output.json"
OUT_HTML = HERE / "preview.html"
MODEL_LIVE = os.environ.get("AGENT2_MODEL", "claude-sonnet-4-6")
MODEL_OLLAMA = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
# 백엔드 선택: auto(기본) | ollama | claude | offline
BACKEND = os.environ.get("AGENT2_BACKEND", "auto").lower()

# ──────────────────────────────────────────────────────────────────────────
# 고정 JSON 스키마 (tool use input_schema). 변경 금지(공유 계약).
# D-02·03·07·08 은 명세 4-1절 원본, 나머지(D-01·04·05·09·10)는 같은 패턴으로 확장.
# ──────────────────────────────────────────────────────────────────────────
TOOLS = {
    # D-01 기본정보
    "extract_basic_info": {
        "name": "extract_basic_info",
        "description": "사업명/발주기관/사업유형 등 기본정보를 추출한다. 원문 명시값만.",
        "input_schema": {"type": "object", "properties": {
            "business_name": {"type": "string"},
            "ordering_agency": {"type": "string"},
            "business_type": {"type": "string", "enum": ["용역", "R&D", "혼합", "기타"]},
            "evidence_page": {"type": "integer"},
        }, "required": ["business_name", "evidence_page"]},
    },
    # D-02 기간
    "extract_period": {
        "name": "extract_period",
        "description": "사업기간/연구개발기간/접수기간/제출기한 등 날짜를 추출한다. YYYY-MM-DD 정규화.",
        "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {
            "type": "object", "properties": {
                "period_type": {"type": "string", "enum": ["사업기간", "연구개발기간", "당해연도기간", "접수기간", "제출기한", "기타"]},
                "start_date": {"type": "string"}, "end_date": {"type": "string"},
                "has_time": {"type": "boolean"}, "deadline_time": {"type": "string"},
                "evidence_page": {"type": "integer"}, "source_text": {"type": "string"},
            }, "required": ["period_type", "end_date", "evidence_page", "source_text"]}}},
            "required": ["items"]},
    },
    # D-03 예산
    "extract_budget": {
        "name": "extract_budget",
        "description": "예산/금액 항목을 추출한다. 추정 금지, 원문 명시값만.",
        "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {
            "type": "object", "properties": {
                "budget_type": {"type": "string", "enum": ["소요예산", "정부지원연구개발비", "기관부담금", "계약금액", "기타"]},
                "amount": {"type": "number"}, "currency": {"type": "string", "enum": ["KRW"]},
                "vat_included": {"type": "boolean"}, "evidence_page": {"type": "integer"}, "source_text": {"type": "string"},
            }, "required": ["budget_type", "amount", "evidence_page", "source_text"]}}},
            "required": ["items"]},
    },
    # D-04 계약/선정 방식
    "extract_contract_method": {
        "name": "extract_contract_method",
        "description": "계약방식 또는 선정평가방식을 추출한다.",
        "input_schema": {"type": "object", "properties": {
            "method": {"type": "string"}, "evidence_page": {"type": "integer"}, "source_text": {"type": "string"},
        }, "required": ["method", "evidence_page"]},
    },
    # D-05 과업
    "extract_tasks": {
        "name": "extract_tasks",
        "description": "주요 과업/요구사항 항목을 추출한다.",
        "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {
            "type": "object", "properties": {
                "task": {"type": "string"}, "importance": {"type": "string", "enum": ["필수", "권고", "참고"]},
                "evidence_page": {"type": "integer"},
            }, "required": ["task", "evidence_page"]}}},
            "required": ["items"]},
    },
    # D-07 평가배점
    "extract_evaluation_table": {
        "name": "extract_evaluation_table",
        "description": "평가항목별 배점 표를 추출한다. 배점 합계 검증용.",
        "input_schema": {"type": "object", "properties": {
            "items": {"type": "array", "items": {"type": "object", "properties": {
                "category": {"type": "string"}, "parent_category": {"type": "string"},
                "score": {"type": "number"}, "criteria_text": {"type": "string"}, "evidence_page": {"type": "integer"},
            }, "required": ["category", "score", "evidence_page"]}},
            "total_score": {"type": "number"}}, "required": ["items"]},
    },
    # D-08 제출서류
    "extract_submission_documents": {
        "name": "extract_submission_documents",
        "description": "제출서류 목록과 필수 여부를 추출한다. 누락 위험 탐지용.",
        "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {
            "type": "object", "properties": {
                "doc_name": {"type": "string"}, "required": {"type": "string", "enum": ["필수", "선택", "해당시"]},
                "format": {"type": "string"}, "quantity": {"type": "string"}, "evidence_page": {"type": "integer"},
            }, "required": ["doc_name", "required", "evidence_page"]}}},
            "required": ["items"]},
    },
    # D-09 보안/안전
    "extract_security_safety": {
        "name": "extract_security_safety",
        "description": "보안/안전 관련 요건을 추출한다.",
        "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {
            "type": "object", "properties": {
                "requirement": {"type": "string"}, "kind": {"type": "string", "enum": ["보안", "안전"]},
                "evidence_page": {"type": "integer"},
            }, "required": ["requirement", "kind", "evidence_page"]}}},
            "required": ["items"]},
    },
    # D-10 산출물
    "extract_outputs": {
        "name": "extract_outputs",
        "description": "사업 수행 산출물/납품물을 추출한다(제출서류와 구분).",
        "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {
            "type": "object", "properties": {
                "output_name": {"type": "string"}, "cycle": {"type": "string"}, "evidence_page": {"type": "integer"},
            }, "required": ["output_name", "evidence_page"]}}},
            "required": ["items"]},
    },
}

PYTYPE = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}


def validate(value, schema, path="$"):
    errs = []
    t = schema.get("type")
    if t:
        if t in ("number", "integer") and isinstance(value, bool):
            errs.append(f"{path}: bool 은 {t} 가 아님")
        elif not isinstance(value, PYTYPE[t]):
            errs.append(f"{path}: 타입 불일치(기대 {t}, 실제 {type(value).__name__})")
    if t == "object" and isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}.{req}: 필수 필드 누락")
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                errs += validate(value[k], sub, f"{path}.{k}")
    elif t == "array" and isinstance(value, list):
        for i, item in enumerate(value):
            errs += validate(item, schema["items"], f"{path}[{i}]")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: enum 위반(값 '{value}' ∉ {schema['enum']})")
    return errs


def link_evidence(page_no, evidence):
    hits = [e["evidence_id"] for e in evidence if e["page_no"] == page_no]
    return hits[0] if hits else None


# ──────────────────────────────────────────────────────────────────────────
# C. 문서 분류 (용역/R&D/혼합 + confidence) — 키워드 신호 기반
# ──────────────────────────────────────────────────────────────────────────
SERVICE_SIGNALS = ["용역", "유지보수", "협상에 의한 계약", "과업", "계약방식"]
RND_SIGNALS = ["연구개발비", "정부지원연구개발", "선정평가", "IRIS", "국가연구개발", "연구개발기간", "성과지표"]


def classify_document(full_text):
    s = sum(full_text.count(k) for k in SERVICE_SIGNALS)
    r = sum(full_text.count(k) for k in RND_SIGNALS)
    tags, total = [], (s + r) or 1
    if s:
        tags.append({"type": "용역", "signals": s})
    if r:
        tags.append({"type": "R&D", "signals": r})
    if s and r and min(s, r) / total >= 0.25:
        primary, conf = "혼합", round(1 - abs(s - r) / total, 2)
    elif s >= r:
        primary, conf = "용역", round(s / total, 2)
    else:
        primary, conf = "R&D", round(r / total, 2)
    return {"document_type": primary, "confidence": conf, "multi_tags": tags}


# ──────────────────────────────────────────────────────────────────────────
# E. 요약 (오프라인: 추출 결과 템플릿 / 라이브: Claude 산문 + evidence)
# ──────────────────────────────────────────────────────────────────────────
def make_summary(results, classification):
    bi = results.get("extract_basic_info", {})
    budgets = results.get("extract_budget", {}).get("items", [])
    periods = results.get("extract_period", {}).get("items", [])
    evals = results.get("extract_evaluation_table", {}).get("items", [])
    biz_period = next((p for p in periods if p["period_type"] == "사업기간"), None)
    amount = budgets[0]["amount"] if budgets else None
    tech = sum(e["score"] for e in evals if e.get("parent_category") == "기술평가")
    price = sum(e["score"] for e in evals if e.get("parent_category") == "가격평가")
    parts = []
    if bi.get("ordering_agency") and bi.get("business_name"):
        parts.append(f"{bi['ordering_agency']}의 '{bi['business_name']}'({classification['document_type']})")
    if biz_period:
        parts.append(f"사업기간 {biz_period.get('start_date','?')}~{biz_period['end_date']}")
    if amount:
        parts.append(f"예산 {amount:,}원")
    if tech or price:
        parts.append(f"평가 기술{tech}:가격{price}")
    return {"one_line": ", ".join(parts) + ".", "analysis_type": "summary"}


# ──────────────────────────────────────────────────────────────────────────
# OFFLINE 추출 디스패치
# ──────────────────────────────────────────────────────────────────────────
def offline_extract(doc):
    pages = {p["page_no"]: p["text"] for p in doc["pages"]}
    full = "\n".join(pages.values())
    out = {}

    # D-01 기본정보
    bi = {"evidence_page": 2}
    m = re.search(r"사업명[:：]?\s*([^\n나다라마]+)", full)
    if m:
        bi["business_name"] = m.group(1).strip(" .")
    m = re.search(r"(발주기관|발주처)[:：]?\s*([^\n다라마]+)", full)
    if m:
        bi["ordering_agency"] = m.group(2).strip(" .")
    m = re.search(r"사업유형[:：]?\s*([가-힣A-Za-z]+)", full)
    if m:
        bt = m.group(1).strip()
        bi["business_type"] = bt if bt in ["용역", "R&D", "혼합"] else "기타"
    out["extract_basic_info"] = bi

    # D-02 기간
    items = []
    for pno, txt in pages.items():
        for m in re.finditer(r"(사업기간|연구개발기간|접수기간)[:：]?\s*(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})", txt):
            items.append({"period_type": m.group(1), "start_date": m.group(2), "end_date": m.group(3),
                          "has_time": False, "evidence_page": pno, "source_text": m.group(0)})
        m = re.search(r"제출마감[:：]?\s*(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})", txt)
        if m:
            items.append({"period_type": "제출기한", "end_date": m.group(1), "has_time": True,
                          "deadline_time": m.group(2), "evidence_page": pno, "source_text": m.group(0)})
    out["extract_period"] = {"items": items}

    # D-03 예산
    items = []
    for pno, txt in pages.items():
        m = re.search(r"소요예산[:：]?\s*금?([\d,]+)\s*원", txt)
        if m:
            items.append({"budget_type": "소요예산", "amount": int(m.group(1).replace(",", "")),
                          "currency": "KRW", "vat_included": ("부가가치세 포함" in txt or "부가세 포함" in txt),
                          "evidence_page": pno, "source_text": m.group(0)})
    out["extract_budget"] = {"items": items}

    # D-04 계약방식
    cm = {"evidence_page": 1}
    m = re.search(r"(협상에 의한 계약|제한경쟁입찰|일반경쟁입찰|수의계약|선정평가)", full)
    if m:
        cm["method"] = m.group(1); cm["source_text"] = m.group(0)
        cm["evidence_page"] = next((p["page_no"] for p in doc["pages"] if m.group(1) in p["text"]), 1)
    out["extract_contract_method"] = cm

    # D-05 과업
    items = []
    for pno, txt in pages.items():
        if "과업" not in txt:
            continue
        for m in re.findall(r"[가나다라마]\.\s*([^가-힣]*[가-힣][^.]*?)(?=\s+[나다라마]\.|\s*$)", txt):
            t = m.strip(" .")
            if len(t) >= 4:
                items.append({"task": t, "evidence_page": pno})
    out["extract_tasks"] = {"items": items}

    # D-07 평가배점 — mock(dict rows)과 agent1 실파싱(grid rows / records) 모두 지원
    items, total = [], None
    for tb in doc.get("tables", []):
        if "평가" not in (tb.get("title") or "") and "배점" not in (tb.get("title") or ""):
            continue
        # 1) mock 형식: rows = [{"항목","배점","상위"?}, ...]
        for r in tb.get("rows", []):
            if isinstance(r, dict) and "항목" in r and "배점" in r:
                items.append({"category": r["항목"], "parent_category": r.get("상위", ""),
                              "score": r["배점"], "evidence_page": tb["page_no"]})
        # 2) agent1 실파싱 형식: records = [{헤더:값,...}] — 점수로 보이는 숫자 열 탐색
        for rec in tb.get("records", []) or []:
            cat = next((str(v) for v in rec.values() if v and not str(v).strip().replace(".", "").isdigit()), "")
            sc = next((float(re.sub(r"[^\d.]", "", str(v))) for v in rec.values()
                       if re.fullmatch(r"\s*\d+(\.\d+)?\s*점?\s*", str(v) or "")), None)
            if cat and sc is not None:
                items.append({"category": cat[:40], "score": sc, "evidence_page": tb["page_no"]})
        if tb.get("total") is not None:
            total = tb.get("total")
    out["extract_evaluation_table"] = {"items": items}
    if total is not None:
        out["extract_evaluation_table"]["total_score"] = total

    # D-08 제출서류
    items = []
    for pno, txt in pages.items():
        if "제출서류" not in txt and "제안서" not in txt:
            continue
        for name, req in re.findall(r"([가-힣A-Za-z0-9 ]+?)\s*\d*부?\(?(필수|선택|해당시)\)?", txt):
            name = name.strip(" .·가나다라마")
            if len(name) >= 2 and req:
                items.append({"doc_name": name, "required": req, "evidence_page": pno})
    seen, uniq = set(), []
    for it in items:
        k = (it["doc_name"], it["required"])
        if k not in seen:
            seen.add(k); uniq.append(it)
    out["extract_submission_documents"] = {"items": uniq}

    # D-09 보안/안전
    items = []
    for pno, txt in pages.items():
        if "보안" in txt:
            for m in re.findall(r"(보안각서[가-힣 ]*|보안[가-힣 ]*?(?:각서|서약|준수))", txt):
                items.append({"requirement": m.strip(), "kind": "보안", "evidence_page": pno})
        if "안전" in txt:
            for m in re.findall(r"(산업안전보건[가-힣 ]*?(?:확약서|준수확약서)|안전[가-힣 ]*?확약서)", txt):
                items.append({"requirement": m.strip(), "kind": "안전", "evidence_page": pno})
    sN, u = set(), []
    for it in items:
        if it["requirement"] not in sN:
            sN.add(it["requirement"]); u.append(it)
    out["extract_security_safety"] = {"items": u}

    # D-10 산출물
    items = []
    for pno, txt in pages.items():
        for m in re.findall(r"(월간[가-힣 ]*보고서|최종[가-힣 ]*보고서|결과보고서)\s*\(([^)]+)\)", txt):
            items.append({"output_name": m[0].strip(), "cycle": m[1].strip(), "evidence_page": pno})
    out["extract_outputs"] = {"items": items}
    return out


def live_extract(doc, client):
    full_text = "\n".join(f"[p{p['page_no']}] {p['text']}" for p in doc["pages"])
    table_text = json.dumps(doc.get("tables", []), ensure_ascii=False)
    out = {}
    for tool_name, tool in TOOLS.items():
        prompt = (f"다음은 제안요청서(RFP) 원문이다. 페이지는 [pN]으로 표기됨.\n표: {table_text}\n\n"
                  f"원문:\n{full_text}\n\n위에서 '{tool['description']}' 추정 금지, 원문 명시값만, evidence_page 필수.")
        resp = client.messages.create(model=MODEL_LIVE, max_tokens=2048, tools=[tool],
                                      tool_choice={"type": "tool", "name": tool_name},
                                      messages=[{"role": "user", "content": prompt}])
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        out[tool_name] = block.input if block else {}
    return out


# ──────────────────────────────────────────────────────────────────────────
# OLLAMA 추출 — 로컬 소형 모델(qwen2.5:3b 등). MiMo 같은 대형모델 로컬 불가 대체용.
# Claude의 tool_choice 강제 대신 Ollama structured output(format=JSON 스키마)로 형식 강제.
# 추가 의존성 없이 stdlib urllib로 /api/chat 호출. 같은 9종 스키마·검증 재사용.
# ──────────────────────────────────────────────────────────────────────────
def ollama_available():
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as r:
            tags = json.loads(r.read().decode("utf-8"))
        names = [m.get("name", "") for m in tags.get("models", [])]
        return any(n == MODEL_OLLAMA or n.split(":")[0] == MODEL_OLLAMA.split(":")[0] for n in names)
    except Exception:
        return False


def _ollama_chat(prompt, schema):
    """format=JSON 스키마로 출력 형식을 강제하고 파싱된 dict를 반환."""
    body = json.dumps({
        "model": MODEL_OLLAMA,
        "messages": [{"role": "user", "content": prompt}],
        "format": schema,           # Ollama structured output: 스키마 강제
        "stream": False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read().decode("utf-8"))
    content = resp.get("message", {}).get("content", "").strip()
    return json.loads(content) if content else {}


def ollama_extract(doc, only=None):
    full_text = "\n".join(f"[p{p['page_no']}] {p['text']}" for p in doc["pages"])
    table_text = json.dumps(doc.get("tables", []), ensure_ascii=False)
    out = {}
    for tool_name, tool in TOOLS.items():
        if only is not None and tool_name not in only:
            continue
        prompt = (f"다음은 제안요청서(RFP) 원문이다. 페이지는 [pN]으로 표기됨.\n표: {table_text}\n\n"
                  f"원문:\n{full_text}\n\n위에서 '{tool['description']}'\n"
                  f"규칙: 추정 금지, 원문에 명시된 값만, evidence_page 필수, 주어진 JSON 스키마를 정확히 따를 것.")
        try:
            out[tool_name] = _ollama_chat(prompt, tool["input_schema"])
        except Exception as e:
            print(f"[warn] ollama {tool_name} 실패({e}) → 빈 결과", file=sys.stderr)
            out[tool_name] = {}
    return out


# ──────────────────────────────────────────────────────────────────────────
# HYBRID 추출 — 정형값(예산/기간/배점/제출서류)은 정규식으로 정확히,
# 서술·판단(기본정보/계약방식/과업/보안/산출물)은 LLM(Ollama) 또는 규칙으로.
# 인라인 텍스트와 agent1이 뽑아준 표(rows 그리드/header) 양쪽을 모두 읽는다.
# 소형 LLM의 정형값 누락/0값 문제를 결정적(deterministic) 정규식으로 보완.
# ──────────────────────────────────────────────────────────────────────────
_DATE = r"(\d{4})\s*[.\-년]\s*(\d{1,2})\s*[.\-월]\s*(\d{1,2})"


def _ymd(y, m, d):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def _unit_mult(text):
    """표 '단위: 백만원' 류에서 곱수를 구한다."""
    if "백만원" in text:
        return 1_000_000
    if "천원" in text:
        return 1_000
    if "억원" in text:
        return 100_000_000
    return None


def regex_budget(doc):
    items = []
    # 1) 인라인: '소요예산 … 금250,000,000원'
    for p in doc["pages"]:
        for m in re.finditer(r"(소요예산|사업비|연구개발비|계약금액|정부지원[가-힣]*|총사업비)\D{0,10}금?\s*([\d,]{4,})\s*원", p["text"]):
            bt = "정부지원연구개발비" if "연구개발비" in m.group(1) else ("계약금액" if "계약" in m.group(1) else "소요예산")
            ctx = p["text"][max(0, m.start() - 30):m.end() + 30]
            items.append({"budget_type": bt, "amount": int(m.group(2).replace(",", "")), "currency": "KRW",
                          "vat_included": ("부가" in ctx), "evidence_page": p["page_no"], "source_text": m.group(0)[:80]})
    # 2) 표: '단위: 백만원' + 연구개발비/예산 키워드 → 행별 첫 숫자셀 × 곱수
    for t in doc.get("tables", []):
        htext = " ".join(str(h) for h in (t.get("header") or [])) + " " + (t.get("title") or "")
        mult = _unit_mult(htext)
        if mult is None or not re.search(r"연구개발비|예산|사업비|지원금|금액", htext):
            continue
        for r in t.get("rows", [])[1:]:
            cell = next((c for c in r if re.fullmatch(r"\s*[\d,]+(\.\d+)?\s*", c or "") and float(c.replace(",", "")) > 0), None)
            if cell:
                items.append({"budget_type": "정부지원연구개발비" if "연구개발비" in htext else "소요예산",
                              "amount": int(float(cell.replace(",", "")) * mult), "currency": "KRW", "vat_included": False,
                              "evidence_page": t["page_no"], "source_text": f"{cell} [{htext.strip()[:24]}]"[:80]})
    return {"items": items}


def regex_period(doc):
    items = []
    for p in doc["pages"]:
        txt = p["text"]
        for m in re.finditer(_DATE + r"\s*~\s*" + _DATE, txt):
            g = m.groups()
            pre = txt[max(0, m.start() - 16):m.start()]
            ptype = "연구개발기간" if "연구개발" in pre else ("사업기간" if "사업기간" in pre or "사업 기간" in pre else "기타")
            items.append({"period_type": ptype, "start_date": _ymd(*g[0:3]), "end_date": _ymd(*g[3:6]),
                          "has_time": False, "evidence_page": p["page_no"], "source_text": m.group(0)[:60]})
        for m in re.finditer(r"(제출\s*마감|접수\s*마감|제출기한|마감일시?)\D{0,12}" + _DATE + r"(?:\D{0,6}(\d{1,2}):(\d{2}))?", txt):
            g = m.groups()
            has_t = g[4] is not None
            it = {"period_type": "제출기한", "end_date": _ymd(*g[1:4]), "has_time": has_t,
                  "evidence_page": p["page_no"], "source_text": m.group(0)[:60]}
            if has_t:
                it["deadline_time"] = f"{int(g[4]):02d}:{g[5]}"
            items.append(it)
    # 표 셀: 절대날짜 범위 + 상대기간('N년/개월 이내') — R&D 공고는 기간이 표 안인 경우가 많다
    for t in doc.get("tables", []):
        htext = " ".join(str(h) for h in (t.get("header") or [])) + " " + (t.get("title") or "")
        is_period_tbl = bool(re.search(r"연구개발기간|사업기간|총\s*기간", htext))
        for r in t.get("rows", [])[1:]:
            for cell in r:
                cell = cell or ""
                for m in re.finditer(_DATE + r"\s*~\s*" + _DATE, cell):
                    g = m.groups()
                    items.append({"period_type": "연구개발기간" if "연구개발" in htext else "사업기간",
                                  "start_date": _ymd(*g[0:3]), "end_date": _ymd(*g[3:6]), "has_time": False,
                                  "evidence_page": t["page_no"], "source_text": m.group(0)[:60]})
                md = re.search(r"(\d+\s*년(?:\s*\d+\s*개?월)?|\d+\s*개?월)\s*이내", cell)
                if md and is_period_tbl:
                    items.append({"period_type": "연구개발기간", "end_date": "", "has_time": False,
                                  "duration": md.group(0).strip(), "evidence_page": t["page_no"],
                                  "source_text": cell.strip()[:60]})
    # 중복 제거
    seen, uniq = set(), []
    for it in items:
        k = (it["period_type"], it.get("end_date"), it.get("duration"), it.get("source_text"))
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    return {"items": uniq}


def regex_evaluation(doc):
    items, total = [], None
    for t in doc.get("tables", []):
        header = [str(h) for h in (t.get("header") or [])]
        htext = " ".join(header) + " " + (t.get("title") or "")
        if not re.search(r"배점|평가항목|점수", htext):
            continue
        cat_i = next((i for i, h in enumerate(header) if re.search(r"평가항목|항목|구\s?분|성과", h)), 0)
        sc_i = next((i for i, h in enumerate(header) if re.search(r"배점|점수", h)), None)
        if sc_i is None:
            continue
        for r in t.get("rows", [])[1:]:
            if len(r) <= max(cat_i, sc_i):
                continue
            cat = (r[cat_i] or "").strip()
            m = re.search(r"\d+(\.\d+)?", r[sc_i] or "")
            if cat and m:
                items.append({"category": cat[:40], "score": float(m.group(0)), "evidence_page": t["page_no"]})
    # mock 형식(dict rows) 백업
    for t in doc.get("tables", []):
        for r in t.get("rows", []):
            if isinstance(r, dict) and "항목" in r and "배점" in r:
                items.append({"category": r["항목"], "parent_category": r.get("상위", ""),
                              "score": r["배점"], "evidence_page": t["page_no"]})
                if t.get("total") is not None:
                    total = t["total"]
    out = {"items": items}
    if total is not None:
        out["total_score"] = total
    return out


def regex_submission(doc):
    items, seen = [], set()
    for p in doc["pages"]:
        for name, req in re.findall(r"([가-힣A-Za-z0-9 ()]{2,40}?)\s*\d*부?\s*\(?(필수|선택|해당시)\)?", p["text"]):
            name = name.strip(" .·:()가나다라마0123456789")
            if len(name) >= 2 and (name, req) not in seen:
                seen.add((name, req))
                items.append({"doc_name": name, "required": req, "evidence_page": p["page_no"]})
    return {"items": items}


def parser_basic_info(doc):
    """D-01: opendataloader-pdf 파서의 title/목차에서 사업명·발주기관 추출(결정적)."""
    pages = {p["page_no"]: p["text"] for p in doc["pages"]}
    p1 = pages.get(1, "")
    cands = [o["title"].strip() for o in doc.get("outline", [])
             if o.get("page_no") == 1 and re.search(r"공고|사업|과제|개발|용역", o["title"]) and "목 차" not in o["title"]]
    bn = max(cands, key=len) if cands else (doc.get("outline", [{}])[0].get("title", doc["file_name"]))
    bi = {"business_name": bn.strip()[:120], "evidence_page": 1}
    m = (re.search(r"([가-힣]{2,}(?:부|청|위원회|진흥원|공단|연구원|기상청|진흥회))\s*공고", p1)
         or re.search(r"(?:주관기관|발주기관|전문기관|발주처)\D{0,4}[:：(]?\s*([가-힣()·\s]{2,20})", p1))
    if m:
        bi["ordering_agency"] = m.group(1).strip()[:40]
    return bi


def regex_contract_method(doc):
    """D-04: 선정/계약 방식(지정공모, 협상에 의한 계약 등) — 목차+본문 정규식."""
    blob = " ".join(o["title"] for o in doc.get("outline", [])) + " " + " ".join(p["text"] for p in doc["pages"])
    m = re.search(r"(지정공모|품목지정공모|자유공모|공모형|협상에 의한 계약|제한경쟁입찰|일반경쟁입찰|수의계약|선정평가)", blob)
    cm = {"evidence_page": 1}
    if m:
        cm["method"] = m.group(1)
        cm["evidence_page"] = next((p["page_no"] for p in doc["pages"] if m.group(1) in p["text"]), 1)
        cm["source_text"] = m.group(0)
    return cm


def parser_tasks(doc):
    """D-05: 파서 목차의 과업/사업내용 계열 heading + 리스트를 과업 항목으로."""
    items, seen = [], set()
    for o in doc.get("outline", []):
        t = o["title"].strip()
        if "목 차" in t or len(t) < 4:
            continue
        if re.match(r"^[□ㅇ\-*•]|사업목적|사업내용|공모과제|주요\s*과업|과업|연구개발\s*내용|추진\s*내용|성과목표", t):
            task = t.lstrip("□ㅇ-*• ").strip()[:80]
            if task and task not in seen:
                seen.add(task)
                items.append({"task": task, "evidence_page": o.get("page_no")})
    return {"items": items[:30]}


def regex_security(doc):
    """D-09: 보안/안전 요건."""
    items, seen = [], set()
    for p in doc["pages"]:
        for m in re.findall(r"(보안과제|보안[가-힣 ]*?(?:각서|서약|준수|등급|유지)|비밀[가-힣 ]*?(?:준수|유지))", p["text"]):
            k = m.strip()[:60]
            if k and k not in seen:
                seen.add(k); items.append({"requirement": k, "kind": "보안", "evidence_page": p["page_no"]})
        for m in re.findall(r"(산업안전보건[가-힣 ]*|안전[가-힣 ]*?(?:확약서|준수|관리))", p["text"]):
            k = m.strip()[:60]
            if k and k not in seen:
                seen.add(k); items.append({"requirement": k, "kind": "안전", "evidence_page": p["page_no"]})
    return {"items": items[:15]}


def regex_outputs(doc):
    """D-10: 산출물/보고서."""
    items, seen = [], set()
    for p in doc["pages"]:
        for m in re.findall(r"(최종\s*보고서|연차\s*보고서|중간\s*보고서|결과\s*보고서|착수\s*보고서|월간[가-힣 ]*보고서|산출물|납품물)", p["text"]):
            k = re.sub(r"\s+", " ", m.strip())
            if k and k not in seen:
                seen.add(k); items.append({"output_name": k, "evidence_page": p["page_no"]})
    return {"items": items[:15]}


def hybrid_extract(doc):
    """전 항목을 opendataloader-pdf 파서 출력 + 정규식으로 결정적 추출.
    파서가 준 title/목차/표를 직접 쓰므로 소형 LLM의 빈값/0값 문제가 없다.
    (옵션) AGENT2_HYBRID_LLM=1 이면 그래도 빈 항목만 Ollama로 보강."""
    out = {
        "extract_basic_info": parser_basic_info(doc),
        "extract_period": regex_period(doc),
        "extract_budget": regex_budget(doc),
        "extract_contract_method": regex_contract_method(doc),
        "extract_tasks": parser_tasks(doc),
        "extract_evaluation_table": regex_evaluation(doc),
        "extract_submission_documents": regex_submission(doc),
        "extract_security_safety": regex_security(doc),
        "extract_outputs": regex_outputs(doc),
    }
    if os.environ.get("AGENT2_HYBRID_LLM") == "1" and ollama_available():
        empty = [k for k, v in out.items()
                 if not (v.get("items") or v.get("business_name") or v.get("method"))]
        print(f"[hybrid] 파서+정규식(결정적) | 빈 항목 {empty} 만 Ollama 보강")
        if empty:
            out.update(ollama_extract(doc, only=empty))
    else:
        print("[hybrid] 전 항목 = opendataloader-pdf 파서 + 정규식 (결정적, Ollama 미사용)")
    return out


def attach_evidence_ids(results, evidence):
    for payload in results.values():
        if isinstance(payload, dict):
            if "evidence_page" in payload:
                payload["evidence_id"] = link_evidence(payload["evidence_page"], evidence)
            for it in payload.get("items", []):
                if "evidence_page" in it:
                    it["evidence_id"] = link_evidence(it["evidence_page"], evidence)


def detect_risks(results):
    """E-06 누락 위험 탐지: 필수 제출서류/제출기한 관점 간단 점검."""
    risks = []
    subs = results.get("extract_submission_documents", {}).get("items", [])
    if not any(s["required"] == "필수" for s in subs):
        risks.append("필수 제출서류가 식별되지 않음 — 확인 필요")
    if not any(p["period_type"] == "제출기한" for p in results.get("extract_period", {}).get("items", [])):
        risks.append("제출기한(마감)이 식별되지 않음 — 확인 필요")
    ev = results.get("extract_evaluation_table", {})
    if ev.get("items"):
        s = sum(i["score"] for i in ev["items"])
        if ev.get("total_score") is not None and s != ev["total_score"]:
            risks.append(f"평가배점 합계 불일치(항목합 {s} ≠ 명시 {ev['total_score']})")
    return risks

def build_html(doc, bundle):
    c = bundle["classification"]; bi = bundle["fields"]["extract_basic_info"]
    summ = bundle["summary"]["one_line"]
    budgets = bundle["fields"]["extract_budget"]["items"]
    periods = bundle["fields"]["extract_period"]["items"]
    evals = bundle["fields"]["extract_evaluation_table"]["items"]
    subs = bundle["fields"]["extract_submission_documents"]["items"]
    risks = bundle["risks"]

    def ev_tag(it):
        return f"<sup class='ev'>{it.get('evidence_id','-')}</sup>"

    rows = "".join(
        f"<tr><td>{e.get('parent_category','')}</td><td>{e['category']}</td>"
        f"<td style='text-align:right'>{e['score']}{ev_tag(e)}</td></tr>" for e in evals)
    subs_html = "".join(
        f"<li>{s['doc_name']} <b class='req-{s['required']}'>{s['required']}</b>{ev_tag(s)}</li>" for s in subs)
    period_html = "".join(
        f"<li>{p['period_type']}: {p.get('start_date','')}~{p['end_date']}"
        f"{' '+p.get('deadline_time','') if p.get('has_time') else ''}{ev_tag(p)}</li>" for p in periods)
    budget_html = "".join(
        f"<li>{b['budget_type']}: {b['amount']:,}원 {'(VAT포함)' if b.get('vat_included') else ''}{ev_tag(b)}</li>"
        for b in budgets)
    risk_html = "".join(f"<li>⚠️ {r}</li>" for r in risks) or "<li>위험 없음 ✅</li>"

    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>agent2 분석 미리보기</title><style>
body{{font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:24px}}
.card{{max-width:760px;margin:0 auto;background:#1e293b;border-radius:14px;padding:24px;box-shadow:0 8px 24px rgba(0,0,0,.4)}}
h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#94a3b8;font-size:13px;margin-bottom:16px}}
.badge{{display:inline-block;background:#2563eb;color:#fff;border-radius:999px;padding:2px 10px;font-size:12px;margin-right:6px}}
.conf{{color:#38bdf8;font-size:12px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}}
section{{background:#0f172a;border-radius:10px;padding:14px}} section h3{{margin:0 0 8px;font-size:13px;color:#7dd3fc}}
ul{{margin:0;padding-left:18px;font-size:13px;line-height:1.7}} table{{width:100%;border-collapse:collapse;font-size:13px}}
td{{padding:3px 6px;border-bottom:1px solid #334155}} .ev{{color:#64748b;font-size:9px;margin-left:3px}}
.req-필수{{color:#f87171}} .req-선택{{color:#fbbf24}} .req-해당시{{color:#94a3b8}}
.summary{{background:#172554;border-left:3px solid #3b82f6;padding:10px 12px;border-radius:6px;font-size:14px;margin-top:8px}}
.risk{{grid-column:1/3;background:#3f1d1d;border-radius:10px;padding:14px}} .risk h3{{color:#fca5a5}}
</style></head><body><div class="card">
<h1>{bi.get('business_name','(사업명 미상)')}</h1>
<div class="sub">{doc['file_name']} · 발주: {bi.get('ordering_agency','-')}</div>
<span class="badge">{c['document_type']}</span><span class="conf">confidence {c['confidence']}</span>
<div class="summary">📋 {summ}</div>
<div class="grid">
<section><h3>예산</h3><ul>{budget_html}</ul></section>
<section><h3>기간</h3><ul>{period_html}</ul></section>
<section><h3>평가배점</h3><table>{rows}</table></section>
<section><h3>제출서류</h3><ul>{subs_html}</ul></section>
<div class="risk"><h3>누락 위험(E-06)</h3><ul>{risk_html}</ul></div>
</div></div></body></html>"""


def main():
    # 입력: 기본은 mock, AGENT1_OUTPUT 환경변수로 agent1 실제 파싱 결과로 교체 가능
    src = Path(os.environ["AGENT1_OUTPUT"]) if os.environ.get("AGENT1_OUTPUT") else MOCK
    doc = json.loads(src.read_text(encoding="utf-8"))
    print(f"[입력원] {src.name}")
    evidence = doc.get("evidence", [])
    full_text = "\n".join(p["text"] for p in doc["pages"])

    # 백엔드 결정: 명시(AGENT2_BACKEND) 우선, 없으면 auto(ollama→claude→offline)
    mode, client = "OFFLINE", None
    want = BACKEND
    if want == "auto":
        if ollama_available():
            want = "ollama"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            want = "claude"
        else:
            want = "offline"

    if want == "hybrid":
        mode = "HYBRID"
    elif want == "ollama":
        if ollama_available():
            mode = "OLLAMA"
        else:
            print(f"[warn] OLLAMA 불가(서버 미실행 또는 {MODEL_OLLAMA} 미설치) → OFFLINE 폴백", file=sys.stderr)
    elif want in ("claude", "live"):
        if os.environ.get("ANTHROPIC_API_KEY"):
            try:
                import anthropic
                client = anthropic.Anthropic(); mode = "LIVE"
            except Exception as e:
                print(f"[warn] LIVE 불가({e}) → OFFLINE 폴백", file=sys.stderr)
        else:
            print("[warn] ANTHROPIC_API_KEY 없음 → OFFLINE 폴백", file=sys.stderr)

    model_label = {"LIVE": MODEL_LIVE, "OLLAMA": MODEL_OLLAMA,
                   "HYBRID": f"정규식+{MODEL_OLLAMA if ollama_available() else '규칙'}"}.get(mode, "규칙기반")
    print(f"=== agent2 분석 | 모드: {mode} | 모델: {model_label} ===")
    print(f"입력: {doc['file_name']} (status={doc['status']})\n")

    if mode == "LIVE":
        fields = live_extract(doc, client)
    elif mode == "OLLAMA":
        fields = ollama_extract(doc)
    elif mode == "HYBRID":
        fields = hybrid_extract(doc)
    else:
        fields = offline_extract(doc)

    # 스키마 검증
    total_errs = 0
    for name, payload in fields.items():
        errs = validate(payload, TOOLS[name]["input_schema"])
        print(f"[스키마검증] {name}: {'PASS ✅' if not errs else f'FAIL ❌({len(errs)})'}")
        for e in errs:
            print(f"    - {e}")
        total_errs += len(errs)

    attach_evidence_ids(fields, evidence)
    classification = classify_document(full_text)
    summary = make_summary(fields, classification)
    risks = detect_risks(fields)

    # 배점 합계 검증
    ev = fields.get("extract_evaluation_table", {})
    if ev.get("items"):
        s = sum(i["score"] for i in ev["items"])
        ok = ev.get("total_score") is None or s == ev["total_score"]
        print(f"\n[배점합계검증] 항목합={s}, 명시={ev.get('total_score')} {'일치 ✅' if ok else '불일치 ⚠️'}")

    print(f"\n[분류] {classification['document_type']} (confidence {classification['confidence']}) "
          f"tags={[t['type'] for t in classification['multi_tags']]}")
    print(f"[요약] {summary['one_line']}")
    print(f"[누락위험] {risks if risks else '없음 ✅'}")

    bundle = {
        "document_id": doc["document_id"], "file_name": doc["file_name"],
        "classification": classification, "fields": fields, "summary": summary, "risks": risks,
    }
    OUT_JSON.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_HTML.write_text(build_html(doc, bundle), encoding="utf-8")

    n_fields = sum(len(p.get("items", [])) if "items" in p else 1 for p in fields.values())
    print(f"\n=== 산출 ===")
    print(f"  - {OUT_JSON.name} (통합 분석 결과, 추출 {n_fields}건)")
    print(f"  - {OUT_HTML.name} (대시보드 데모 미리보기)")
    print(f"\n=== DoD ===")
    print(f"  - 9종 도구 출력 스키마 100% 준수: {'예 ✅' if total_errs == 0 else '아니오 ❌'}")
    print(f"  - 분류/요약/누락위험 생성: 예 ✅")
    return 0 if total_errs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
