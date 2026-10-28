"""Read-only: identify + guidance for the questions whose results changed under H1. DATABASE_URL picks the DB."""
import os, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app
c = TestClient(app)
print("DB:", os.environ.get("DATABASE_URL", "procedureassist (.env)").rsplit("/", 1)[-1])
for q in ("When is a duplicate driving licence issued?", "I lost my DL, what should I do?"):
    b = c.post("/api/identify", json={"question": q, "language": "en"}).json()
    print(f"\n### {q} -> {b['status']} {[x['name'] for x in b.get('candidates', [])]}")
    if b["status"] == "matched":
        r = c.post("/api/guidance", json={"procedure_id": b["candidates"][0]["id"], "question": q, "language": "en"}).json()
        print(f"   insufficient={r['insufficient_evidence']} partial={r.get('partial')}")
        for x in r["claims"]:
            print(f"   - {x['text']}\n       quote: {x['quote']!r}")
