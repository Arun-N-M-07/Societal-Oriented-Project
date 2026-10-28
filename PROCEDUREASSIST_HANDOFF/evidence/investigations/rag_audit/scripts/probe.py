"""Read-only RAG audit probe: real /api/identify and /api/guidance (as the citizen page calls them),
plus page scores and the rank of the evidence chunk in the expected page. DATABASE_URL picks the DB.
Writes nothing to any database. The questions are audit probes, not evaluation fixtures."""
import json, re, sys, time
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure, ProcedureChunk
from backend.procedure_search import rank_procedures

c = TestClient(app)
# (group, question, expected page id(s), evidence regex the cited quote should contain, follow-up context page id)
PROBES = [
    ("P", "What is the minimum age for a transport vehicle licence?", [22], r"twenty", None),
    ("P", "Can I apply at 20?", [22], r"twenty", None),
    ("P", "Am I eligible for a commercial driving licence?", [22], r"twenty", None),
    ("P", "Can a 19-year-old obtain this licence?", [22], r"twenty", None),
    ("P", "What's the age requirement for a transport DL?", [22], r"twenty", None),
    ("P", "How old must I be to drive a truck or bus?", [22], r"twenty", None),
    ("P", "I am 19. Can I get a licence to drive a lorry?", [22], r"twenty", None),
    ("V", "How much do I pay to get my DL renewed?", [27, 24], r"200", None),
    ("V", "My licence got stolen, what now?", [25], r"lost", None),
    ("V", "I sold my bike. What does the buyer have to do and by when?", [30], r"fourteen|Form 30", None),
    ("V", "My dad passed away; can I keep using his car?", [30], r"three months", None),
    ("V", "How do I get my name on the voters list?", [19], r"Form 6", None),
    ("V", "I work in Dubai. Can I vote in India?", [21], r"Form 6A|overseas", None),
    ("V", "What's the charge to fix my address in Aadhaar at the post office?", [35], r"₹ ?50|₹ ?75", None),
    ("V", "Is it free to get a new Aadhaar made at the post office?", [35], r"free", None),
    ("V", "When can I take out my whole PF money?", [36], r"58|retire|unemploy", None),
    ("V", "How much does my boss put into my PF?", [36], r"12", None),
    ("V", "What does the family get from EDLI if a worker dies?", [38], r"lakh", None),
    ("V", "Which papers do I carry to get an international permit?", [26], r"Passport|Visa", None),
    ("V", "How much pension can I get under APY?", [40, 34], r"1,?000|5,?000", None),
    ("V", "Can I renew my DL early?", [24], r"one month", None),
    ("B", "Can an NRI file ITR-1?", [33], r"Non-Resident|NRI", None),
    ("B", "What is the income limit for filing ITR-1?", [33], r"50 lakh", None),
    ("B", "Can I use ITR-1 if I have capital gains?", [33], r"capital gain", None),
    ("B", "What do I need before filing ITR-2 online?", [16], r"bank account|user ID|PAN", None),
    ("B", "Which Aadhaar details can I update?", [18], r"Name, Address|Demographic Information", None),
    ("B", "Can I update my Aadhaar address online?", [18], r"online mode", None),
    ("B", "What is the fee to renew the RC of a motorcycle?", [39], r"Motor ?cycle Rupees Three Hundred", None),
    ("B", "What is the fitness test fee for a motorcycle?", [39], r"fitness: \(a\) Motorcycle", None),
    ("B", "How much does a duplicate RC cost?", [39], r"duplicate certificate of registration", None),
    ("B", "What is the hypothecation endorsement fee for a car?", [39], r"hypothecation agreement: \(b\)", None),
    ("B", "What do I need before linking PAN with Aadhaar?", [31], r"Prerequisites|valid PAN", None),
    ("B", "How do I register on the income tax e-filing portal?", [32], r"[Rr]egister", None),
    ("M", "What are the eligibility requirements, required documents and application steps for a permanent driving licence?", [23], r"Form 4|Learner", None),
    ("M", "Who can file ITR-1, which documents do I need and what are the steps to file it?", [33], r"Resident Individual|Step 1", None),
    ("M", "For a passport, what documents do I need, what is the fee and how do I apply?", [15], r"Passport Seva|appointment|Apply", None),
    ("M", "For EPF, who is eligible, how much is contributed and when can I withdraw?", [36], r"12|58|15,000", None),
    ("F", "What about a transport vehicle?", [22], r"twenty", 22),
    ("F", "And if I apply late?", [24], r"30 days|five years", 24),
    ("F", "What if the owner died?", [30], r"three months|Form 31", 30),
    ("F", "And how much does it cost?", [26, 27], r"1000", 26),
    ("F", "What about EPS?", [37], r"EPS|pension", 36),
]

with SessionLocal() as db:
    pages = {p.id: p for p in db.query(Procedure)}
    counts = {pid: db.query(ProcedureChunk).filter_by(procedure_id=pid).count() for pid in pages}

    def evidence_rank(pid, question, ev):
        ordered = rag.retrieve(db, pid, question, limit=counts[pid])
        return next((r for r, ch in enumerate(ordered, 1) if re.search(ev, ch.content)), None)

    def guidance(pid, question):
        return c.post("/api/guidance", json={"procedure_id": pid, "question": question, "language": "en"}).json()

    for group, q, expected, ev, context in PROBES:
        t = time.time()
        vector = rag.embed_texts([q], query=True)[0]
        top = [(pid, round(s, 3)) for pid, s in rank_procedures(db, vector)]
        if context:  # the citizen page: the open page first, then a new search only if it cannot answer
            target, ident = context, {"status": f"follow-up on {context}"}
            reply = guidance(target, q)
            if reply["insufficient_evidence"]:
                ident = c.post("/api/identify", json={"question": q, "language": "en"}).json()
                if ident["status"] == "matched" and ident["candidates"][0]["id"] != target:
                    target = ident["candidates"][0]["id"]
                    reply = guidance(target, q)
        else:
            ident = c.post("/api/identify", json={"question": q, "language": "en"}).json()
            target = ident["candidates"][0]["id"] if ident.get("status") == "matched" else None
            reply = guidance(target, q) if target else None
        exp_rank = {pid: evidence_rank(pid, q, ev) for pid in expected}
        status = ident.get("status")
        cands = [x["id"] for x in ident.get("candidates", [])] if "candidates" in ident else []
        if reply is None:
            outcome = "clarification" if ident.get("clarification") else f"{status} {cands}"
        elif reply["insufficient_evidence"]:
            outcome = "abstained"
        else:
            hit = any(re.search(ev, cl["quote"]) for cl in reply["claims"])
            outcome = f"{len(reply['claims'])} claims{' partial' if reply.get('partial') else ''}, evidence {'CITED' if hit else 'not cited'}"
        print(json.dumps({"group": group, "q": q, "expected": expected, "status": status, "candidates": cands,
                          "answered_page": target, "top3": top, "evidence_rank_in_expected": exp_rank,
                          "outcome": outcome, "claims": [cl["text"] for cl in (reply or {}).get("claims", [])],
                          "secs": round(time.time() - t)}, ensure_ascii=False), flush=True)
