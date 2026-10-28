"""Read-only trace of the two Tamil Nadu certificate questions through the real API with the current code:
identify -> procedure card -> guidance, recording the model's draft claims, what verify_claims kept, and what the
meaning check (check_claims) kept. DATABASE_URL picks the database; nothing is written."""
import json, os, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend import rag
from backend.main import app

QUESTIONS = ["What documents are needed for an income certificate in Tamil Nadu?",
             "What documents do I need for a nativity certificate in Tamil Nadu?"]
steps = []
real_verify, real_check = rag.verify_claims, rag.check_claims

def verify(claims, passages):
    kept = real_verify(claims, passages)
    steps.append({"stage": "verify_claims", "drafted": claims, "kept": kept})
    return kept

def check(question, claims, chunks):
    kept, complete = real_check(question, claims, chunks)
    steps.append({"stage": "check_claims", "in": len(claims), "kept": kept, "complete": complete})
    return kept, complete

rag.verify_claims, rag.check_claims = verify, check
client = TestClient(app)
print("DB:", os.environ.get("DATABASE_URL", "procedureassist").rsplit("/", 1)[-1])
for q in QUESTIONS:
    steps.clear()
    ident = client.post("/api/identify", json={"question": q, "language": "en"}).json()
    out = {"question": q, "identify": ident.get("status"), "candidates": [(c["id"], c["name"]) for c in ident.get("candidates", [])]}
    if ident.get("status") == "matched":
        pid = ident["candidates"][0]["id"]
        card = client.get(f"/api/procedures/{pid}").json()
        out["card_shown"] = {"name": card["name"], "summary": card["summary"], "steps": card["steps"], "eligibility": card["eligibility"]}
        reply = client.post("/api/guidance", json={"procedure_id": pid, "question": q, "language": "en"}).json()
        out["reply"] = {k: reply.get(k) for k in ("insufficient_evidence", "partial", "omitted_claims")}
        out["final_claims"] = [{"text": c["text"], "quote": c["quote"], "chunk_id": c["chunk_id"]} for c in reply["claims"]]
        out["steps"] = steps[:]
    print(json.dumps(out, ensure_ascii=False, indent=1))
