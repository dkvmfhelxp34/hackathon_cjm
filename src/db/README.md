# agent3용 — SQLite 조회 가이드 (대시보드가 DB 읽는 법)

> **이 문서의 목적**: agent3(React 대시보드)가 `proposal.db`(SQLite)에서 분석 결과를 **어떻게 읽는지**
> 한 번에 알 수 있게 정리. agent3는 SQL을 직접 짜지 말고 **`query.py`의 조회 함수만** 호출하면 된다.
> 상세 스키마/적재 규칙은 루트 `agent2_db_manager.md` 참조.

---

## 0. 30초 요약

```
PDF →[agent1 파싱]→ JSON ─┐
                          ├─[load_to_db.py]→ src/db/proposal.db ─[query.py 함수]→ 대시보드
     [agent2 분석]→ JSON ─┘
```
- DB 파일: `src/db/proposal.db` (없으면 `python3 load_to_db.py`로 생성)
- 읽기 API: `src/db/query.py` 함수 9종 (모두 JSON 직렬화 가능한 dict/list 반환)
- 추가 의존성 0 (Python 표준 `sqlite3`)

---

## 1. DB 준비 (한 번)

```bash
cd src/agent1 && ./run.sh <input.pdf> --with-agent2   # JSON 산출
cd ../db && python3 load_to_db.py                      # → proposal.db 생성
```

---

## 2. 조회 함수 = 화면 데이터 소스 (명세서 3.2 GET 대응)

| 함수 | 화면 용도 | 반환 |
|---|---|---|
| `list_documents()` | 문서 목록 화면 | `[{document_id, file_name, document_type, number_of_pages, status}]` |
| `get_document(id)` | 상세 헤더 | 문서 메타 1건 |
| `get_classification(id)` | 유형 배지/confidence | `{document_type, confidence, multi_tags, _model}` |
| `get_summary(id)` | 1페이지 요약 카드 | `{one_line, analysis_type, _model}` |
| `get_fields(id)` | 기본정보/예산/기간 컬럼 | `[{field_name, field_value, confidence, evidence_id}]` |
| `get_requirements(id, req_type?)` | 과업/제출서류/보안 탭 | `[{req_type, req_text, importance, page_no}]` |
| `get_evaluation(id)` | 평가배점 표 + 합계 | `{items:[...], score_sum}` |
| `get_deliverables(id)` | 산출물 목록 | `[{deliverable_name, due_date, format}]` |
| `get_risks(id)` | 누락 위험 경고 | `["...위험 문구..."]` |

---

## 3. 실제 반환 예시 (RD1.pdf = 해양수산부 R&D 공고)

```jsonc
// list_documents()
[{ "document_id":"DOC-41EDFD82D2", "file_name":"RD1.pdf",
   "document_type":"R&D", "number_of_pages":37, "status":"extracted" }]

// get_classification(id)
{ "document_type":"R&D", "confidence":1.0,
  "multi_tags":[{"type":"R&D","signals":54}], "_model":"hybrid(parser+regex)" }

// get_summary(id)
{ "one_line":"해양수산부의 '2026년도 민군경 AI 기반 해양영상 … 공고'(R&D), 예산 15,000,000,000원.",
  "analysis_type":"summary", "_model":"hybrid(parser+regex)" }

// get_fields(id)  ← 표준 field_name 키
[ {"field_name":"business_name",   "field_value":"2026년도 … 공고", "evidence_id":"EV-001-01"},
  {"field_name":"ordering_agency", "field_value":"해양수산부",      "evidence_id":"EV-001-01"},
  {"field_name":"contract_method", "field_value":"지정공모",        "evidence_id":"EV-001-01"},
  {"field_name":"budget:정부지원연구개발비", "field_value":"15000000000", "evidence_id":"EV-036-01"},
  {"field_name":"period:연구개발기간",       "field_value":"4년 이내",     "evidence_id":"EV-001-01"} ]

// get_evaluation(id)
{ "items":[ {"category":"연구개발 계획 (40%)","score":10.0,"evidence_id":"EV-016-01"}, … ],
  "score_sum":53.0 }

// get_requirements(id, "과업")
[ {"req_type":"과업","req_text":"사업목적","importance":null,"page_no":3}, … ]

// get_risks(id)
[ "제출기한(마감)이 식별되지 않음 — 확인 필요" ]
```

> `field_name` 표준값(대시보드 컬럼 키): `business_name`, `ordering_agency`, `business_type`,
> `contract_method`, `budget:{유형}`, `period:{유형}`. 전체 정의는 `agent2_db_manager.md` 3.1.
> `evidence_id`는 `evidence_map` 테이블의 원문 근거로 연결된다(근거 표시/하이라이트용).

---

## 4. agent3 연동 방법 — 두 가지 패턴

### 패턴 A) Python에서 직접 import (가장 간단)
```python
import sys; sys.path.append("src/db")
import query as q
doc_id = q.list_documents()[0]["document_id"]
summary = q.get_summary(doc_id)          # dict → 그대로 화면에
evaluation = q.get_evaluation(doc_id)
```

### 패턴 B) React용 REST 래퍼 (FastAPI 8줄)
React는 SQLite를 직접 못 읽으니, query 함수를 HTTP로 노출한다:
```python
# src/db/api.py (예시)
from fastapi import FastAPI
import query as q
app = FastAPI()
app.get("/api/documents")(lambda: q.list_documents())
app.get("/api/documents/{id}/summary")(lambda id: q.get_summary(id))
app.get("/api/documents/{id}/evaluation")(lambda id: q.get_evaluation(id))
app.get("/api/documents/{id}/requirements")(lambda id, req_type=None: q.get_requirements(id, req_type))
app.get("/api/documents/{id}/risks")(lambda id: q.get_risks(id))
# 실행: uvicorn api:app --port 8002  → React fetch('http://localhost:8002/api/...')
```
React는 `fetch()`로 위 엔드포인트를 호출해 탭별 데이터를 렌더하면 된다.

---

## 5. 화면 탭 ↔ 함수 매핑 (제안)

| 대시보드 탭(명세서 9.3) | 호출 함수 |
|---|---|
| 문서 목록 | `list_documents()` |
| 요약 | `get_summary` + `get_classification` + `get_fields` |
| 과업/요구사항 | `get_requirements(id, "과업")`, `…("제출서류")`, `…("보안")` |
| 평가 대응 | `get_evaluation` (score_sum으로 배점 합 표시) |
| 산출물 | `get_deliverables` |
| 누락 위험 | `get_risks` |

---

## 6. 주의

- DB는 **읽기 전용**으로 쓴다(분석 데이터). agent3가 쓰는 건 `tasks` 테이블(담당자/상태)뿐.
- `proposal.db`는 생성물이라 git에 없음(.gitignore). 위 1절로 각자 생성.
- 같은 입력이면 적재 결과 동일(결정적, hybrid 백엔드 기준). 모델 추적은 `_model` 필드 참고.
