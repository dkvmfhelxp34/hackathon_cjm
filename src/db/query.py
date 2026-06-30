#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
query.py — 대시보드(agent3)가 쓰는 조회 함수 모음 (DB 읽기 전용 API).

명세서 3.2의 GET 엔드포인트에 1:1 대응한다. agent3는 REST를 붙이든 직접 import 하든
이 함수들만 호출하면 된다. 모든 함수는 dict/list[dict]를 반환(JSON 직렬화 가능).

  list_documents()                 → 문서 목록
  get_document(id)                 → 메타 + 분류
  get_classification(id)           → 분류(유형/confidence/태그)
  get_fields(id)                   → D-01~ 추출 필드(표준 field_name)
  get_summary(id)                  → 요약(E-01)
  get_requirements(id)             → 요구사항(과업/제출서류/보안/안전)
  get_evaluation(id)               → 평가배점 + 합계검증
  get_deliverables(id)             → 산출물/제출서류
  get_risks(id)                    → 누락 위험(E-06)

실행(데모): python3 query.py [document_id]
"""
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
DEFAULT_DB = HERE / "proposal.db"


def _conn(db=DEFAULT_DB):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    return c


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


def list_documents(db=DEFAULT_DB):
    with _conn(db) as c:
        return _rows(c.execute(
            "SELECT document_id,file_name,document_type,number_of_pages,status FROM documents ORDER BY created_at DESC"))


def get_document(doc_id, db=DEFAULT_DB):
    with _conn(db) as c:
        r = c.execute("SELECT * FROM documents WHERE document_id=?", (doc_id,)).fetchone()
        return dict(r) if r else None


def _analysis(c, doc_id, atype):
    r = c.execute("SELECT result_json,model_name FROM analysis_results WHERE document_id=? AND analysis_type=?"
                  " ORDER BY result_id DESC LIMIT 1", (doc_id, atype)).fetchone()
    if not r:
        return None
    out = json.loads(r["result_json"])
    out["_model"] = r["model_name"]
    return out


def get_classification(doc_id, db=DEFAULT_DB):
    with _conn(db) as c:
        return _analysis(c, doc_id, "classification")


def get_summary(doc_id, db=DEFAULT_DB):
    with _conn(db) as c:
        return _analysis(c, doc_id, "summary")


def get_risks(doc_id, db=DEFAULT_DB):
    with _conn(db) as c:
        r = _analysis(c, doc_id, "risks")
        return (r or {}).get("risks", [])


def get_fields(doc_id, db=DEFAULT_DB):
    with _conn(db) as c:
        return _rows(c.execute(
            "SELECT field_name,field_value,confidence,evidence_id FROM extracted_fields WHERE document_id=?",
            (doc_id,)))


def get_requirements(doc_id, req_type=None, db=DEFAULT_DB):
    sql = "SELECT req_type,req_text,importance,page_no FROM requirements WHERE document_id=?"
    params = [doc_id]
    if req_type:
        sql += " AND req_type=?"
        params.append(req_type)
    with _conn(db) as c:
        return _rows(c.execute(sql, params))


def get_evaluation(doc_id, db=DEFAULT_DB):
    with _conn(db) as c:
        items = _rows(c.execute(
            "SELECT category,parent_category,score,criteria_text,evidence_id FROM evaluation_items WHERE document_id=?",
            (doc_id,)))
    total = sum(i["score"] or 0 for i in items)
    return {"items": items, "score_sum": total}


def get_deliverables(doc_id, db=DEFAULT_DB):
    with _conn(db) as c:
        return _rows(c.execute(
            "SELECT deliverable_name,due_date,format FROM deliverables WHERE document_id=?", (doc_id,)))


def _demo(doc_id):
    print(f"=== 문서 {doc_id} 대시보드 조회 데모 ===")
    print("[메타]", json.dumps(get_document(doc_id), ensure_ascii=False)[:120])
    print("[분류]", json.dumps(get_classification(doc_id), ensure_ascii=False))
    print("[요약]", json.dumps(get_summary(doc_id), ensure_ascii=False)[:160])
    ev = get_evaluation(doc_id)
    print(f"[평가배점] {len(ev['items'])}항목 합계 {ev['score_sum']}")
    print(f"[요구사항] 과업 {len(get_requirements(doc_id,'과업'))} / 제출서류 {len(get_requirements(doc_id,'제출서류'))}")
    print(f"[산출물] {len(get_deliverables(doc_id))}건")
    print(f"[누락위험] {get_risks(doc_id)}")


def main():
    if not DEFAULT_DB.exists():
        print(f"[오류] DB 없음: {DEFAULT_DB}\n  먼저: python3 load_to_db.py", file=sys.stderr)
        return 2
    if len(sys.argv) > 1:
        _demo(sys.argv[1])
    else:
        docs = list_documents()
        print("문서 목록:", json.dumps(docs, ensure_ascii=False))
        if docs:
            print()
            _demo(docs[0]["document_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
