# DB 매니저 작업 명세 — 데이터 적재·저장소·조회 API

> 이 문서는 **DB 매니저 역할**을 정의한다. agent1(파싱)과 agent2(분석)가 만든 JSON 산출물을
> 공유 SQLite DB(명세서 10장 스키마)에 적재하고, agent3(대시보드)이 읽을 **조회 API**를 제공한다.
> 구현체: `src/db/schema.sql`, `src/db/load_to_db.py`, `src/db/query.py`. (작성: 마경림)

---

## 0. 역할과 위치

이 계층은 분석 결과의 **단일 진실 공급원(single source of truth)** 이다. 세 에이전트가 JSON으로만
주고받던 데이터를 DB에 모아, 대시보드가 일관된 스키마로 조회하게 한다.

```
PDF →[agent1] agent1_output.json ─┐
                                  ├─[DB 매니저: load_to_db.py]→ proposal.db ─[agent3: query.py]→ 대시보드
     [agent2] agent2_output.json ─┘                                 ▲
                                                          (조회 전용 API, GET 대응)
```

핵심 책임:
1. agent1 산출(documents/pages/evidence)을 적재한다.
2. agent2 산출(분류/추출/요약/리스크)을 표준 테이블에 적재하고 `documents.document_type`을 갱신한다.
3. agent3가 화면을 그릴 수 있는 **조회 함수(REST GET 대응)** 를 제공한다.
4. 같은 입력 → 같은 적재(결정적), 재적재는 idempotent(문서 단위 교체).

> 비책임: 추출/분류 로직(=agent2), 화면/리포트(=agent3), 시크릿 보관(키는 환경변수, DB 비저장 — 명세서 4.3).

---

## 1. 입력 계약 (무엇을 적재하는가)

| 입력 | 출처 | 사용 키 |
|---|---|---|
| `agent1_output.json` | agent1 파서(opendataloader-pdf) | `document_id, file_name, status, number_of_pages, doc_hint, needs_ocr, pages[], evidence[]` |
| `agent2_output.json` | agent2 추출기(hybrid/claude/ollama) | `classification, fields{...}, summary, risks` |

두 JSON의 키 구조는 `src/agent2/mock_agent1_output.json`(입력 계약 예시)·`src/agent1/README.md`(출력 계약)와 호환된다.

---

## 2. 데이터베이스 스키마 (명세서 10장)

정의는 `src/db/schema.sql`. MVP는 SQLite(확장 시 PostgreSQL). 테이블별 쓰기 주체:

| 테이블 | 쓰기 주체 | 핵심 컬럼 |
|---|---|---|
| `documents` | agent1 적재 + agent2가 `document_type` 갱신 | document_id(PK), file_name, status, document_type, number_of_pages, needs_ocr |
| `document_pages` | agent1 | (document_id, page_no, text, image_path) |
| `evidence_map` | agent1 | evidence_id(PK), page_no, text |
| `extracted_fields` | DB 매니저(agent2 산출) | field_name, field_value, confidence, evidence_id |
| `requirements` | DB 매니저 | req_type(과업/제출서류/평가/보안/안전/산출물), req_text, importance, page_no |
| `evaluation_items` | DB 매니저 | category, parent_category, score, criteria_text |
| `deliverables` | DB 매니저 | deliverable_name, due_date, format |
| `proposal_sections` | DB 매니저 | section_type(common/service/rnd/missing), title, description |
| `analysis_results` | DB 매니저 | analysis_type(summary/classification/risks), result_json, model_name, tokens |
| `api_cache` | DB 매니저 | request_hash(UNIQUE), response_json (중복 호출 방지) |
| `tasks` | **agent3** (여기선 정의만) | assignee, state |

---

## 3. 적재 매핑 규칙 (load_to_db.py)

agent2의 `fields`를 표준 테이블로 변환한다. **표준 `field_name`을 여기서 확정**한다(구 미해결이슈 #2 해소).

### 3.1 extracted_fields 표준 field_name
| field_name | 출처 | 예 |
|---|---|---|
| `business_name` | extract_basic_info.business_name | "2026년도 … 개발 사업 … 공고" |
| `ordering_agency` | extract_basic_info.ordering_agency | "해양수산부" |
| `business_type` | extract_basic_info.business_type | "R&D" |
| `contract_method` | extract_contract_method.method | "지정공모" |
| `budget:{유형}` | extract_budget.items[] | `budget:정부지원연구개발비` = 15000000000 |
| `period:{유형}` | extract_period.items[] | `period:연구개발기간` = "4년 이내" 또는 YYYY-MM-DD |

### 3.2 그 외 테이블
- `evaluation_items` ← extract_evaluation_table.items (category/parent_category/score/evidence).
- `requirements` ← extract_tasks(req_type=과업), extract_submission_documents(제출서류), extract_security_safety(보안/안전).
- `deliverables` ← extract_outputs + extract_submission_documents(format).
- `analysis_results` ← classification / summary / risks 를 각 1행(result_json=원본 JSON, model_name 기록).

### 3.3 idempotency
재적재 시 같은 `document_id`의 행을 모든 분석 테이블에서 지우고 다시 넣는다(`clear_document`).
→ 같은 입력으로 몇 번을 돌려도 DB 상태가 동일(결정적).

---

## 4. 조회 API (query.py) — agent3 대시보드가 호출

명세서 3.2 GET 엔드포인트에 1:1 대응. agent3는 REST로 감싸거나 직접 import 한다.

| 함수 | 대응 엔드포인트 | 반환 |
|---|---|---|
| `list_documents()` | GET /api/documents | 문서 목록 |
| `get_document(id)` | GET /api/documents/{id} | 메타+분류 |
| `get_classification(id)` | GET /api/analysis/{id}/classification | 유형/confidence/태그 |
| `get_fields(id)` | GET /api/analysis/{id}/fields | 표준 field 목록 |
| `get_summary(id)` | GET /api/analysis/{id}/summary | 요약(E-01) |
| `get_requirements(id, req_type?)` | GET /api/analysis/{id}/requirements | 요구사항(분류 필터) |
| `get_evaluation(id)` | GET /api/analysis/{id}/evaluation | 배점 + 합계 |
| `get_deliverables(id)` | — | 산출물/제출서류 |
| `get_risks(id)` | GET /api/analysis/{id}/risks | 누락 위험 |

모든 반환은 JSON 직렬화 가능한 dict/list.

---

## 5. 실행 (재현 절차)

```bash
# 0) 선행: agent1·agent2 산출 JSON 생성
cd src/agent1 && ./run.sh <input.pdf> --with-agent2     # agent1_output.json + agent2_output.json

# 1) DB 적재 (stdlib sqlite3, 추가 의존성 없음 — python3 기본으로 충분)
cd ../db && python3 load_to_db.py
#   → proposal.db 생성, 적재 행수 출력

# 2) 조회(대시보드 시뮬레이션)
python3 query.py                 # 첫 문서 자동
python3 query.py <document_id>   # 특정 문서
```

`proposal.db`는 생성물이므로 git에 커밋하지 않는다(.gitignore).

---

## 6. 완료 기준 (Definition of Done)

- [x] agent1+agent2 JSON이 10장 스키마로 적재된다(`load_to_db.py`).
- [x] `documents.document_type`이 분류 결과로 갱신된다.
- [x] extracted_fields 표준 field_name이 본 문서 3.1로 확정·적재된다.
- [x] evaluation_items 배점 합계를 조회 시 재계산 제공(`get_evaluation.score_sum`).
- [x] 모든 근거가 evidence_id/page_no로 연결되어 조회된다.
- [x] 재적재 idempotent(문서 단위 교체).
- [x] 조회 API가 3.2 GET에 대응하고 JSON을 반환한다.

### 검증된 결과 (RD1.pdf, 해양수산부 R&D 공고 37p)
```
적재: pages 37 · evidence 120 · fields 5 · requirements 30 · evaluation 7 · analysis 3
조회: 분류 R&D(conf 1.0) · 예산 15,000,000,000원 · 평가배점 7항목 · 과업 27 · 누락위험 1건
```

---

## 7. 주의사항

- **시크릿 비저장**: ANTHROPIC_API_KEY 등은 환경변수로만, DB/로그/소스에 남기지 않는다(명세서 4.3).
- **결정적 적재**: 추출 단계가 파서+정규식(hybrid)일 때 입력이 같으면 DB도 항상 동일. LLM 백엔드를 쓰면 결과가 달라질 수 있으니 `analysis_results.model_name`으로 재현성 추적.
- **다중 태그**: 혼합형은 `analysis_results(classification).multi_tags`에 보존(단일 컬럼 `document_type`은 대표값) → 구 미해결이슈 #4 대응.
- **api_cache**: request_hash로 동일 호출 캐싱(LLM 백엔드 사용 시 비용 절감). hybrid(정규식)는 호출이 없어 캐시 불필요.
