"""Read-only trace of one answer on a freshly ingested unseen page: the page goes through the real Extract and Approve
routes into the *_test database inside one transaction that is always rolled back (as scripts/evaluate_ingestion.py),
then /api/guidance runs with wrappers recording the retrieved chunks, the model's draft claims, what verify_claims kept
and what the meaning check kept.   answer_trace.py <url> <question> [<question> ...]"""
import json, os, sys
from pathlib import Path
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg2://localhost:5432/procedureassist_test")
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend import rag
from backend.auth import require_admin
from backend.database import engine, get_db, get_read_only_db
from backend.routes import router
assert (engine.url.database or "").endswith("_test")
connection = engine.connect(); transaction = connection.begin()
session = Session(bind=connection, join_transaction_mode="create_savepoint")
app = FastAPI(); app.include_router(router)
app.dependency_overrides[get_db] = lambda: session
app.dependency_overrides[get_read_only_db] = lambda: session
app.dependency_overrides[require_admin] = lambda: "trace"
client = TestClient(app)
steps = []
real = {name: getattr(rag, name) for name in ("retrieve", "verify_claims", "check_claims")}
def retrieve(db, procedure, question, *a, **k):
    chunks = real["retrieve"](db, procedure, question, *a, **k)
    steps.append({"stage": "retrieve", "chunks": [" ".join(c.content.split())[:160] for c in chunks]}); return chunks
def verify(claims, passages):
    kept = real["verify_claims"](claims, passages)
    steps.append({"stage": "verify_claims", "drafted": claims, "kept": kept}); return kept
def check(question, claims, chunks):
    kept, complete = real["check_claims"](question, claims, chunks)
    steps.append({"stage": "check_claims", "in": len(claims), "kept": kept, "complete": complete}); return kept, complete
rag.retrieve, rag.verify_claims, rag.check_claims = retrieve, verify, check
try:
    body = client.post("/api/admin/extract", json={"source_url": sys.argv[1]}).json()
    pid = client.post("/api/admin/procedures", json={"procedure": body["procedure"], "source_text": body["source_text"],
                                                     "provenance_token": body["provenance_token"]}).json()["id"]
    for question in sys.argv[2:]:
        steps.clear()
        reply = client.post("/api/guidance", json={"procedure_id": pid, "question": question}).json()
        print(json.dumps({"question": question, "insufficient_evidence": reply["insufficient_evidence"],
                          "claims": [c["text"] for c in reply["claims"]], "steps": steps}, ensure_ascii=False, indent=1))
finally:
    transaction.rollback(); session.close(); connection.close(); engine.dispose()
