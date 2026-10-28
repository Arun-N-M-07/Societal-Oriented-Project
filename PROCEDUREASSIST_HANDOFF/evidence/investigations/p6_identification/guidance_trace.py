"""Read-only trace of /api/guidance on a stored page: the retrieved chunks, the model's draft claims, what verify_claims
kept and what the meaning check kept. DATABASE_URL picks the database.   guidance_trace.py <page id> <question> [...]"""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend import rag
from backend.main import app
steps = []
real = {name: getattr(rag, name) for name in ("retrieve", "verify_claims", "check_claims")}
def retrieve(db, procedure, question, *a, **k):
    chunks = real["retrieve"](db, procedure, question, *a, **k)
    steps.append(("retrieved", [" ".join(c.content.split())[:120] for c in chunks])); return chunks
def verify(claims, passages):
    kept = real["verify_claims"](claims, passages)
    steps.append(("drafted", [(c.get("text"), c.get("quote")) for c in claims])); steps.append(("verify kept", len(kept))); return kept
def check(question, claims, chunks):
    kept, complete = real["check_claims"](question, claims, chunks)
    steps.append(("meaning check kept", [c.get("text") for c in kept], complete)); return kept, complete
rag.retrieve, rag.verify_claims, rag.check_claims = retrieve, verify, check
client = TestClient(app)
for question in sys.argv[2:]:
    steps.clear()
    reply = client.post("/api/guidance", json={"procedure_id": int(sys.argv[1]), "question": question}).json()
    print(f"## {question}\n   final: {'abstained' if reply['insufficient_evidence'] else [c['text'] for c in reply['claims']]}")
    for step in steps:
        print("  ", *step)
