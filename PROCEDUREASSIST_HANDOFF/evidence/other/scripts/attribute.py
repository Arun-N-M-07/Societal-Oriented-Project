"""Trace the known cases stage by stage (read-only). Uses DATABASE_URL (approved or staging copy)."""
import re, sys, json
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Procedure, ProcedureChunk
from backend.procedure_search import rank_procedures
from backend.rag import retrieve, embed_texts
client = TestClient(app)
# (question, language, open page url part or None, evidence regex or None, note)
CASES = [
 ("What is the fee for a duplicate driving licence?", "en", None, None, "citizen duplicate fee"),
 ("What is the fee for a duplicate driving licence?", "en", "duplicate-licence", None, "citizen duplicate fee, follow-up"),
 ("What is the duplicate licence fee for a driving school?", "en", None, r"5000", "school duplicate fee"),
 ("How much does it cost to renew my driving licence?", "en", None, r"Renewal of driving licence\s+Rs\. 200", "renewal fee"),
 ("How much is the renewal fee?", "en", "content/renewal", r"Rs\. 200|Rs\. 30", "renewal follow-up"),
 ("What is the late fee if I renew my licence more than 30 days after it expires?", "en", "content/renewal", r"Rs\. 30", "late charge"),
 ("What is the fee for the driving test?", "en", None, r"Rs\. 300", "driving test fee"),
 ("What is the fee to renew a driving licence after the grace period?", "en", None, r"grace period", "grace-period fee"),
 ("What documents are accepted as proof of address for Aadhaar update?", "en", None, r"PoA|POA|Proof of Address", "Aadhaar address proof"),
 ("At what age can I get a licence to drive a transport vehicle?", "en", None, r"twenty years", "transport vehicle age"),
 ("How old must a vehicle be for the higher registration renewal fee?", "en", None, r"older than 20 years", "vehicle age fee (Rule 81)"),
 ("What is the fee to renew the registration certificate of my car?", "en", None, r"Six Hundred|Rule 81|rule 81", "RC renewal fee"),
 ("What is the fee for a passport?", "en", None, None, "passport fee (calculator only)"),
 ("What happens at the polling booth when I go to vote?", "en", None, r"First polling official", "polling order"),
 ("How long can I see the VVPAT slip?", "en", None, r"7 seconds", "VVPAT duration"),
 ("I have a learner's licence and want my first full driving licence. What do I do?", "en", None, r"Form 4", "learner vs permanent"),
 ("How much does the central government contribute to the pension fund?", "en", None, r"1\.16%", "EPF vs EPS"),
 ("What is the age limit to join EPF?", "en", None, r"18.54", "EPF age (div text)"),
 ("Can apprentices become EPF members?", "en", None, r"apprentice", "EPF FAQ question text"),
 ("What documents are needed for an income certificate in Tamil Nadu?", "en", None, r"Salary Certificate", "TN income certificate docs"),
 ("ஓட்டுநர் உரிமம் புதுப்பிக்க கட்டணம் எவ்வளவு?", "ta", None, r"Renewal of driving licence", "Tamil renewal fee"),
 ("DL renew panna evlo fees?", "ta", None, r"Renewal of driving licence", "Romanized renewal fee"),
 ("Aadhaar la address change panna enna documents venum?", "ta", None, r"PoA|POA|Proof of Address", "mixed Aadhaar docs"),
 ("What is the fee for a biometric update of Aadhaar at a post office?", "en", None, r"125", "India Post fee row"),
 ("Who can file ITR-1?", "en", None, r"Resident Individual", "unrelated: ITR-1 eligibility"),
 ("Which form should an NRI fill to register as a voter?", "en", None, r"6A", "unrelated: overseas Form 6A"),
 ("Within how many days must I apply for transfer of ownership after buying a vehicle in the same state?", "en", None, r"fourteen days", "unrelated: transfer deadline"),
 ("What is the OTP validity when registering on the e-filing portal?", "en", None, r"15 minutes", "unrelated: e-filing OTP"),
 ("What documents do I need for a community certificate in Tamil Nadu?", "en", None, r"Community Certificate of Father", "TN community docs"),
 ("What is the maximum EDLI benefit?", "en", None, r"7 lakh|600,000", "EDLI conflicting maximum"),
]
cos = lambda a, b: float(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b))
with SessionLocal() as db:
    procs = {p.id: p for p in db.query(Procedure)}
    for q, lang, ctx, ev, note in CASES:
        print(f"\n### {note}: {q!r} [{lang}]" + (f" (open page {ctx})" if ctx else ""))
        holders = [p for p in procs.values() if ev and re.search(ev, p.source_text, re.I)]
        print("  source contains evidence:", [f"{p.id}" for p in holders] if ev else "n/a")
        if ctx:
            pid = next(p.id for p in procs.values() if ctx in p.source_url); query = q
        else:
            body = client.post("/api/identify", json={"question": q, "language": lang}).json()
            query = body.get("normalized_query") or q
            vec = embed_texts([query], query=True)[0]
            top = rank_procedures(db, vec)[:3]
            print(f"  normalized: {query!r}" if query != q else "  (english)", "| identify:", body["status"],
                  [c["id"] for c in body.get("candidates", [])], "| top scores:", [(i, round(s, 3)) for i, s in top],
                  "| clarification:", body.get("clarification"))
            if body["status"] != "matched": continue
            pid = body["candidates"][0]["id"]
        vec = np.array(embed_texts([query], query=True)[0])
        got = retrieve(db, pid, query)
        print(f"  page {pid} {procs[pid].name}; retrieved:", [(c.id, round(cos(vec, np.array(c.embedding)), 3), bool(ev and re.search(ev, c.content, re.I))) for c in got])
        if ev and procs[pid] in holders:
            all_c = db.query(ProcedureChunk).filter_by(procedure_id=pid).all()
            print("  evidence chunks on page:", [(c.id, round(cos(vec, np.array(c.embedding)), 3)) for c in all_c if re.search(ev, c.content, re.I)])
        r = client.post("/api/guidance", json={"procedure_id": pid, "question": query, "language": "en"}).json()
        print("  answer: insufficient=", r["insufficient_evidence"], "partial=", r.get("partial"))
        for c in r["claims"]:
            print(f"    - [{c.get('procedure_id', pid)}/{c['chunk_id']}] {c['text'][:150]}")
