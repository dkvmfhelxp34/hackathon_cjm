#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
load_to_db.py — agent1(파싱) + agent2(분석) 산출 JSON을 공유 SQLite DB로 적재한다.

파이프라인에서의 위치:
  PDF →[agent1]→ agent1_output.json ─┐
                                     ├─[이 적재기]→ proposal.db ─[agent3 대시보드]
       [agent2]→ agent2_output.json ─┘

원칙:
  - 같은 입력 JSON → 같은 적재 결과(결정적). 재적재 시 해당 document_id의 기존 행을 지우고 다시 넣음(idempotent).
  - 표준 스키마(schema.sql, 명세서 10장)에만 쓴다. tasks는 agent3 소유라 건드리지 않음.
  - API 키 등 시크릿은 DB에 저장하지 않는다(명세서 4.3).

실행:
  python3 load_to_db.py                # 기본 경로 자동(src/agent1, src/agent2 산출물)
  python3 load_to_db.py <agent1.json> <agent2.json> [out.db]
"""
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
DEFAULT_A1 = ROOT / "src" / "agent1" / "agent1_output.json"
DEFAULT_A2 = ROOT / "src" / "agent2" / "agent2_output.json"
DEFAULT_DB = HERE / "proposal.db"
SCHEMA = HERE / "schema.sql"


def init_db(conn):
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))


def clear_document(conn, doc_id):
    """재적재 idempotency: 이 문서의 기존 행 제거(tasks 제외)."""
    for tbl in ("document_pages", "evidence_map", "extracted_fields", "requirements",
                "evaluation_items", "deliverables", "proposal_sections", "analysis_results"):
        conn.execute(f"DELETE FROM {tbl} WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE document_id=?", (doc_id,))


def load_agent1(conn, a1):
    doc_id = a1["document_id"]
    conn.execute(
        "INSERT INTO documents(document_id,file_name,status,document_type,number_of_pages,doc_hint,needs_ocr)"
        " VALUES(?,?,?,?,?,?,?)",
        (doc_id, a1.get("file_name"), a1.get("status"), None,
         a1.get("number_of_pages"), a1.get("doc_hint"), int(bool(a1.get("needs_ocr")))))
    conn.executemany(
        "INSERT INTO document_pages(document_id,page_no,text) VALUES(?,?,?)",
        [(doc_id, p["page_no"], p.get("text", "")) for p in a1.get("pages", [])])
    conn.executemany(
        "INSERT OR REPLACE INTO evidence_map(evidence_id,document_id,page_no,text) VALUES(?,?,?,?)",
        [(e["evidence_id"], doc_id, e.get("page_no"), e.get("text", "")) for e in a1.get("evidence", [])])
    return doc_id


def load_agent2(conn, doc_id, a2):
    f = a2.get("fields", {})
    cls = a2.get("classification", {})

    # documents.document_type 갱신(분류 결과)
    conn.execute("UPDATE documents SET document_type=? WHERE document_id=?",
                 (cls.get("document_type"), doc_id))

    # extracted_fields: 기본정보/계약방식/예산/기간 → 표준 field_name
    rows = []
    bi = f.get("extract_basic_info", {})
    for k in ("business_name", "ordering_agency", "business_type"):
        if bi.get(k):
            rows.append((doc_id, k, str(bi[k]), None, bi.get("evidence_id")))
    cm = f.get("extract_contract_method", {})
    if cm.get("method"):
        rows.append((doc_id, "contract_method", cm["method"], None, cm.get("evidence_id")))
    for b in f.get("extract_budget", {}).get("items", []):
        rows.append((doc_id, f"budget:{b['budget_type']}", str(b["amount"]), None, b.get("evidence_id")))
    for p in f.get("extract_period", {}).get("items", []):
        val = p.get("end_date") or p.get("duration") or ""
        rows.append((doc_id, f"period:{p['period_type']}", val, None, p.get("evidence_id")))
    conn.executemany(
        "INSERT INTO extracted_fields(document_id,field_name,field_value,confidence,evidence_id) VALUES(?,?,?,?,?)",
        rows)

    # evaluation_items
    conn.executemany(
        "INSERT INTO evaluation_items(document_id,category,parent_category,score,criteria_text,evidence_id)"
        " VALUES(?,?,?,?,?,?)",
        [(doc_id, e.get("category"), e.get("parent_category"), e.get("score"),
          e.get("criteria_text"), e.get("evidence_id"))
         for e in f.get("extract_evaluation_table", {}).get("items", [])])

    # requirements: 과업 + 제출서류 + 보안/안전
    reqs = []
    for t in f.get("extract_tasks", {}).get("items", []):
        reqs.append((doc_id, "과업", t.get("task"), t.get("importance"), t.get("evidence_page")))
    for s in f.get("extract_submission_documents", {}).get("items", []):
        reqs.append((doc_id, "제출서류", s.get("doc_name"), s.get("required"), s.get("evidence_page")))
    for s in f.get("extract_security_safety", {}).get("items", []):
        reqs.append((doc_id, s.get("kind", "보안"), s.get("requirement"), None, s.get("evidence_page")))
    conn.executemany(
        "INSERT INTO requirements(document_id,req_type,req_text,importance,page_no) VALUES(?,?,?,?,?)", reqs)

    # deliverables: 산출물 + 제출서류(format/부수)
    dels = [(doc_id, o.get("output_name"), None, o.get("cycle"))
            for o in f.get("extract_outputs", {}).get("items", [])]
    dels += [(doc_id, s.get("doc_name"), None, s.get("format"))
             for s in f.get("extract_submission_documents", {}).get("items", [])]
    conn.executemany(
        "INSERT INTO deliverables(document_id,deliverable_name,due_date,format) VALUES(?,?,?,?)", dels)

    # analysis_results: classification / summary / risks
    model = a2.get("model_name") or a2.get("summary", {}).get("model") or "hybrid(parser+regex)"
    ana = [(doc_id, "classification", json.dumps(cls, ensure_ascii=False), model),
           (doc_id, "summary", json.dumps(a2.get("summary", {}), ensure_ascii=False), model),
           (doc_id, "risks", json.dumps({"risks": a2.get("risks", [])}, ensure_ascii=False), model)]
    conn.executemany(
        "INSERT INTO analysis_results(document_id,analysis_type,result_json,model_name) VALUES(?,?,?,?)", ana)


def load(a1_path=DEFAULT_A1, a2_path=DEFAULT_A2, db_path=DEFAULT_DB):
    a1 = json.loads(Path(a1_path).read_text(encoding="utf-8"))
    a2 = json.loads(Path(a2_path).read_text(encoding="utf-8"))
    conn = sqlite3.connect(db_path)
    try:
        init_db(conn)
        doc_id = a1["document_id"]
        clear_document(conn, doc_id)
        load_agent1(conn, a1)
        load_agent2(conn, doc_id, a2)
        conn.commit()
    finally:
        conn.close()
    return db_path, a1["document_id"]


def main():
    args = sys.argv[1:]
    a1 = Path(args[0]) if len(args) > 0 else DEFAULT_A1
    a2 = Path(args[1]) if len(args) > 1 else DEFAULT_A2
    db = Path(args[2]) if len(args) > 2 else DEFAULT_DB
    for p in (a1, a2):
        if not p.exists():
            print(f"[오류] 입력 JSON 없음: {p}\n  먼저 agent1/agent2를 실행하세요.", file=sys.stderr)
            return 2
    db_path, doc_id = load(a1, a2, db)

    # 적재 요약
    conn = sqlite3.connect(db_path)
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t} WHERE document_id=?", (doc_id,)).fetchone()[0]
              for t in ("document_pages", "evidence_map", "extracted_fields", "requirements",
                        "evaluation_items", "deliverables", "analysis_results")}
    dtype = conn.execute("SELECT document_type FROM documents WHERE document_id=?", (doc_id,)).fetchone()[0]
    conn.close()
    print(f"=== DB 적재 완료 → {db_path.name} ===")
    print(f"문서: {doc_id} (분류: {dtype})")
    for t, c in counts.items():
        print(f"  - {t:18s}: {c} 행")
    print(f"\n조회: python3 query.py {doc_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
