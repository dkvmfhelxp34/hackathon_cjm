#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent1_parse.py — agent1(문서 처리 파이프라인) PDF 파서

명세: agent1_document_pipeline.md (A-05 PDF 정규화, B-01 텍스트, B-02 표,
      B-04 목차, B-05 근거, A-07 OCR 필요 판정).

입력 : 원본 PDF 파일 (HWPX/HWP는 별도, 본 모듈은 PDF 담당)
도구 : opendataloader-pdf (https://github.com/opendataloader-project/opendataloader-pdf)
        - Java 11+ 내장, 100% 로컬·오프라인, GPU 불필요.
        - convert(input_path, output_dir, format="json") → 의미 타입 요소 트리.
처리 : opendataloader 출력 트리(kids 재귀) → agent2 입력 계약으로 변환.
출력 : agent1_output.json = agent2가 소비하는 계약
        { document_id, file_name, status, number_of_pages, doc_hint,
          pages[]={page_no,text}, tables[]={table_id,page_no,title,rows...},
          outline[]={level,title,page_no}, evidence[]={evidence_id,page_no,text} }

재현 환경(고정):
  - Python 3.10+ (opendataloader-pdf 요구). 이 저장소 기준: /opt/anaconda3/bin/python3.11
  - Java 11+ (opendataloader-pdf 내장 엔진). 확인: `java -version`
  - 설치: `pip install -U opendataloader-pdf`  (requirements.txt 참조)

실행:
  python3.11 agent1_parse.py <input.pdf>        # 특정 PDF
  python3.11 agent1_parse.py                     # 인자 생략 시 루트의 첫 *.pdf 자동 탐색
  ./run.sh <input.pdf>                           # python3.10+ 자동탐지 + agent2 연결까지
출력은 항상 같은 입력에 대해 동일(결정적). 산출: src/agent1/agent1_output.json
"""
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUT_JSON = HERE / "agent1_output.json"

# 본문 텍스트로 취급할 요소 타입(표/이미지 제외)
TEXT_TYPES = {"heading", "paragraph", "list", "text block", "caption"}
# OCR 필요 판정 임계값(A-07): 페이지 평균 텍스트 길이가 이보다 작으면 스캔본 의심
OCR_MIN_CHARS_PER_PAGE = 30


def walk(node):
    """opendataloader 트리를 깊이우선으로 평탄화(자기 자신 포함)."""
    yield node
    for kid in node.get("kids", []) or []:
        yield from walk(kid)


def cell_text(cell):
    """표 셀(kids 안의 paragraph content)에서 텍스트를 모은다."""
    parts = [k.get("content", "") for k in cell.get("kids", []) or [] if k.get("content")]
    return " ".join(p.strip() for p in parts if p and p.strip()).strip()


def parse_pdf(pdf_path: Path) -> dict:
    """PDF → agent2 입력 계약 dict."""
    try:
        import opendataloader_pdf  # 지연 import: 미설치 환경에서도 모듈 로드는 가능
    except ImportError:
        raise SystemExit(
            "[설치 필요] opendataloader-pdf 가 없습니다.\n"
            f"  현재 Python: {sys.version.split()[0]} (3.10+ 필요)\n"
            "  해결: 3.10+ 인터프리터에서  pip install -U opendataloader-pdf\n"
            "  예)  /opt/anaconda3/bin/python3.11 -m pip install -U opendataloader-pdf")

    with tempfile.TemporaryDirectory() as td:
        opendataloader_pdf.convert(input_path=[str(pdf_path)], output_dir=td, format="json")
        out_files = list(Path(td).glob("*.json"))
        if not out_files:
            raise RuntimeError("opendataloader-pdf 가 JSON을 생성하지 못함")
        tree = json.loads(out_files[0].read_text(encoding="utf-8"))

    nodes = list(walk(tree))
    n_pages = tree.get("number of pages") or max((n.get("page number", 0) for n in nodes), default=0)

    # ── B-01 페이지별 텍스트 ──────────────────────────────────────────────
    page_chunks = {}
    for n in nodes:
        if n.get("type") in TEXT_TYPES and n.get("content"):
            pno = n.get("page number")
            if pno:
                page_chunks.setdefault(pno, []).append(n["content"].strip())
    pages = [{"page_no": p, "text": " ".join(page_chunks.get(p, []))}
             for p in range(1, (n_pages or 0) + 1)]

    # ── B-04 목차(heading → outline) ─────────────────────────────────────
    outline = [{"level": n.get("heading level", 1), "title": n["content"].strip(),
                "page_no": n.get("page number")}
               for n in nodes if n.get("type") == "heading" and n.get("content")]

    # ── B-02 표 추출(table → rows 그리드 + 헤더 추정) ─────────────────────
    tables = []
    headings_sorted = [n for n in nodes if n.get("type") == "heading" and n.get("page number")]
    for i, n in enumerate(nodes, 1):
        if n.get("type") != "table":
            continue
        pno = n.get("page number")
        grid = []
        for row in n.get("rows", []) or []:
            grid.append([cell_text(c) for c in row.get("cells", []) or []])
        # title: 같은 페이지에서 표보다 앞에 나온 가장 가까운 heading/caption
        title = ""
        for h in nodes:
            if h.get("type") in ("caption", "heading") and h.get("page number") == pno and h.get("content"):
                title = h["content"].strip()
                if h.get("type") == "caption":
                    break
        # 헤더 추정: 첫 행을 헤더로 보고 나머지 행을 dict로 변환(가능할 때만)
        header = grid[0] if grid else []
        records = []
        if len(grid) > 1 and header and all(header):
            for r in grid[1:]:
                if len(r) == len(header):
                    records.append({header[j]: r[j] for j in range(len(header))})
        tables.append({
            "table_id": f"T-{len(tables)+1}",
            "page_no": pno,
            "title": title,
            "n_rows": n.get("number of rows"),
            "n_cols": n.get("number of columns"),
            "rows": grid,            # 원본 텍스트 그리드(범용)
            "header": header,
            "records": records,      # 헤더 기반 dict 행(추정 성공 시)
        })

    # ── B-05 근거 매핑(evidence_map) ─────────────────────────────────────
    # heading + paragraph + caption 의 핵심 문장을 페이지별로 근거화.
    evidence = []
    seq = {}
    for n in nodes:
        if n.get("type") in ("heading", "paragraph", "caption") and n.get("content"):
            pno = n.get("page number")
            txt = n["content"].strip()
            if not pno or len(txt) < 4:
                continue
            seq[pno] = seq.get(pno, 0) + 1
            evidence.append({"evidence_id": f"EV-{pno:03d}-{seq[pno]:02d}",
                             "page_no": pno, "text": txt[:200]})

    # ── A-07 OCR 필요 판정 ───────────────────────────────────────────────
    total_chars = sum(len(p["text"]) for p in pages)
    avg = total_chars / max(len(pages), 1)
    needs_ocr = avg < OCR_MIN_CHARS_PER_PAGE

    # ── 문서 메타 ────────────────────────────────────────────────────────
    doc_id = "DOC-" + hashlib.sha1(pdf_path.name.encode("utf-8")).hexdigest()[:10].upper()
    doc_hint = _guess_doc_hint(tree, pages)

    return {
        "document_id": doc_id,
        "file_name": pdf_path.name,
        "status": "extracted",
        "number_of_pages": n_pages,
        "doc_hint": doc_hint,
        "needs_ocr": needs_ocr,
        "pages": pages,
        "tables": tables,
        "outline": outline,
        "evidence": evidence,
    }


def _guess_doc_hint(tree, pages):
    """제목/본문 신호로 문서 성격을 가볍게 추정(분류는 agent2 책임, 여기선 힌트만)."""
    title = (tree.get("title") or "")
    head = " ".join(p["text"] for p in pages[:2])
    blob = title + " " + head
    rnd = len(re.findall(r"연구개발|선정평가|과제|R&D|IRIS|개발 사업", blob))
    svc = len(re.findall(r"용역|유지보수|과업|협상에 의한 계약", blob))
    if rnd and rnd >= svc:
        return "R&D 공고(추정)"
    if svc:
        return "용역 제안요청서(추정)"
    return "미상(agent2 분류 필요)"


def main():
    pdf_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if pdf_arg:
        pdf_path = Path(pdf_arg)
    else:
        cands = sorted(ROOT.glob("temp_*.pdf")) + sorted(ROOT.glob("*.pdf"))
        if not cands:
            print("사용법: python3.11 agent1_parse.py <input.pdf>  (또는 루트에 PDF를 두세요)", file=sys.stderr)
            return 2
        pdf_path = cands[0]

    if not pdf_path.exists():
        print(f"[오류] 파일 없음: {pdf_path}", file=sys.stderr)
        return 2

    print(f"=== agent1 PDF 파서 | 도구: opendataloader-pdf (로컬) ===")
    print(f"입력: {pdf_path.name}\n")

    result = parse_pdf(pdf_path)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 결과 요약 ────────────────────────────────────────────────────────
    print(f"[메타] document_id={result['document_id']} status={result['status']} "
          f"pages={result['number_of_pages']} hint={result['doc_hint']}")
    print(f"[B-01 텍스트] {len(result['pages'])} 페이지 추출")
    print(f"[B-02 표]     {len(result['tables'])} 개 (records 변환 "
          f"{sum(1 for t in result['tables'] if t['records'])}개)")
    print(f"[B-04 목차]   {len(result['outline'])} 개 heading")
    print(f"[B-05 근거]   {len(result['evidence'])} 개 evidence")
    print(f"[A-07 OCR]    needs_ocr={result['needs_ocr']} "
          f"(평균 {sum(len(p['text']) for p in result['pages'])//max(len(result['pages']),1)}자/페이지)")
    print(f"\n=== 산출 ===")
    print(f"  - {OUT_JSON.name}  (agent2 입력 계약: pages/tables/outline/evidence)")
    print(f"  → agent2 연결: AGENT1_OUTPUT={OUT_JSON} 로 agent2_extract.py 입력 교체 가능")
    return 0


if __name__ == "__main__":
    sys.exit(main())
