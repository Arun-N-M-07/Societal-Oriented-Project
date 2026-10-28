"""Read-only W1 exploration: for each follow-up, the current answer on the open page and what /api/identify
returns for the follow-up text alone. DATABASE_URL picks the DB."""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app
from backend import rag
from backend.database import SessionLocal
from backend.procedure_search import rank_procedures
c = TestClient(app)
# (id, kind, open page, follow-up, expected routing)
CASES = [
    ("A1", "cross", 36, "What about EPS?", "switch to 37"),
    ("A2", "cross", 36, "How do I claim EDLI insurance?", "switch to 38"),
    ("A3", "cross", 22, "How do I register to vote?", "switch to 19"),
    ("A4", "cross", 15, "And what about linking PAN with Aadhaar?", "switch to 31"),
    ("A5", "cross-indirect", 19, "What about voters living abroad?", "switch to 21"),
    ("B1", "same", 26, "And how much does it cost?", "stay on 26 (completion from 27 allowed)"),
    ("B2", "same", 23, "What documents are required?", "stay on 23"),
    ("B3", "same", 36, "What is the eligibility?", "stay on 36"),
    ("B4", "same", 15, "What about the application process?", "stay on 15"),
    ("B5", "same", 24, "Can I do it online?", "stay on 24"),
    ("B6", "same", 30, "What if the owner died?", "stay on 30"),
    ("C1", "ambiguous", 36, "What about the pension?", "stay on 36 or ask; never present an EPF fact as EPS"),
    ("C2", "ambiguous", 24, "What is the fee?", "stay on 24 (completion from 27 allowed)"),
    ("C3", "ambiguous", 28, "What about the certificate?", "stay on 28"),
    ("C4", "ambiguous", 18, "Can I do this at a post office?", "stay on 18, or switch to 35 only if confident"),
]
with SessionLocal() as db:
    for cid, kind, open_page, q, expect in CASES:
        ident = c.post("/api/identify", json={"question": q, "language": "en"}).json()
        top = [(p, round(s, 3)) for p, s in rank_procedures(db, rag.embed_texts([q], query=True)[0])]
        g = c.post("/api/guidance", json={"procedure_id": open_page, "question": q, "language": "en"}).json()
        print(json.dumps({"id": cid, "kind": kind, "open": open_page, "q": q, "expected": expect,
                          "identify_alone": [ident.get("status"), [x["id"] for x in ident.get("candidates", [])], bool(ident.get("clarification"))],
                          "top3": top, "open_page_answer": "abstained" if g["insufficient_evidence"] else f"{len(g['claims'])} claims{' partial' if g.get('partial') else ''}",
                          "claims": [(cl.get("procedure_id", open_page), cl["text"][:140]) for cl in g["claims"]]}, ensure_ascii=False), flush=True)
