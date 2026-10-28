"""Identify + guidance for targeted questions through the real API (read-only). DATABASE_URL picks the DB."""
import sys, os
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app
c = TestClient(app)
QS = [("What is the fee for an International Driving Permit?", "en"), ("Who can join Atal Pension Yojana?", "en"),
      ("Driving licence renew panna evlo fees?", "ta"), ("What is the fee for renewing my driving licence after the grace period?", "en"),
      ("How much is the fee to renew a driving licence?", "en"), ("What are the driving licence fees?", "en"),
      ("What is the fee for a duplicate driving licence?", "en"), ("What is the duplicate licence fee for a driving school?", "en"),
      ("How much pension will I get under Atal Pension Yojana?", "en"), ("Can an income tax payer join Atal Pension Yojana?", "en"),
      ("What is the fee to renew the registration certificate of my motorcycle?", "en"),
      ("What is the RC renewal fee for an imported car older than 20 years?", "en"),
      ("I just turned 18 and want to vote.", "en"), ("Can apprentices become EPF members?", "en"),
      ("What documents are needed for an income certificate in Tamil Nadu?", "en"), ("What happens at the polling booth when I go to vote?", "en")]
print("DB:", os.environ.get("DATABASE_URL", "approved").rsplit("/", 1)[-1])
for q, lang in QS:
    b = c.post("/api/identify", json={"question": q, "language": lang}).json()
    line = f"\n### {q} -> {b['status']} {[x['name'] for x in b.get('candidates', [])]}"
    print(line)
    if b["status"] == "matched":
        r = c.post("/api/guidance", json={"procedure_id": b["candidates"][0]["id"], "question": b.get("normalized_query") or q, "language": "en"}).json()
        print(f"   insufficient={r['insufficient_evidence']} partial={r.get('partial')}")
        for x in r["claims"]:
            print(f"   - [{x.get('procedure_id', r['procedure_id'])}] {x['text'][:170]}")
