-- 제안서 요약 대시보드 — 공유 DB 스키마 (명세서 10장)
-- MVP: SQLite. 같은 입력 → 같은 적재(결정적). agent3 대시보드가 읽는다.
-- 쓰기 주체: documents/document_pages/evidence_map=agent1, 분석계열=agent2(DB매니저), tasks=agent3.

PRAGMA foreign_keys = ON;

-- ── agent1 적재 (입력·파싱 계층) ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
  document_id     TEXT PRIMARY KEY,
  file_name       TEXT,
  status          TEXT,            -- uploaded/converting/extracting/extracted/error
  document_type   TEXT,            -- 용역/R&D/혼합 (agent2 분류 후 갱신, 최초 NULL)
  number_of_pages INTEGER,
  doc_hint        TEXT,
  needs_ocr       INTEGER,         -- 0/1
  created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS document_pages (
  document_id TEXT,
  page_no     INTEGER,
  text        TEXT,
  image_path  TEXT,
  PRIMARY KEY (document_id, page_no),
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS evidence_map (
  evidence_id TEXT PRIMARY KEY,
  document_id TEXT,
  page_no     INTEGER,
  text        TEXT,
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

-- ── agent2(DB매니저) 적재 (분석 계층) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS extracted_fields (
  field_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id TEXT,
  field_name  TEXT,                -- 표준값: business_name/ordering_agency/budget:*/period:* 등
  field_value TEXT,
  confidence  REAL,
  evidence_id TEXT,
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS requirements (
  req_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id TEXT,
  req_type    TEXT,                -- 과업/제출서류/평가/보안/안전/산출물
  req_text    TEXT,
  importance  TEXT,                -- 필수/권고/참고
  page_no     INTEGER,
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS evaluation_items (
  eval_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id    TEXT,
  category        TEXT,
  parent_category TEXT,
  score           REAL,
  criteria_text   TEXT,
  evidence_id     TEXT,
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS deliverables (
  deliverable_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id      TEXT,
  deliverable_name TEXT,
  due_date         TEXT,
  format           TEXT,
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS proposal_sections (
  section_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id  TEXT,
  section_type TEXT,               -- common/service/rnd/missing
  title        TEXT,
  description  TEXT,
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS analysis_results (
  result_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id   TEXT,
  analysis_type TEXT,              -- summary/classification/risks 등
  result_json   TEXT,
  model_name    TEXT,
  input_tokens  INTEGER,
  output_tokens INTEGER,
  stop_reason   TEXT,
  created_at    TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS api_cache (
  cache_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id   TEXT,
  request_hash  TEXT UNIQUE,       -- 모델명+프롬프트+도구정의+입력청크 해시
  response_json TEXT,
  model_name    TEXT,
  created_at    TEXT DEFAULT (datetime('now'))
);

-- ── agent3 소유(여기선 정의만, 쓰기는 대시보드가) ────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
  task_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id TEXT,
  req_id      INTEGER,
  assignee    TEXT,
  state       TEXT,                -- todo/doing/done
  updated_at  TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE INDEX IF NOT EXISTS idx_fields_doc  ON extracted_fields(document_id);
CREATE INDEX IF NOT EXISTS idx_reqs_doc    ON requirements(document_id);
CREATE INDEX IF NOT EXISTS idx_eval_doc    ON evaluation_items(document_id);
CREATE INDEX IF NOT EXISTS idx_results_doc ON analysis_results(document_id);
