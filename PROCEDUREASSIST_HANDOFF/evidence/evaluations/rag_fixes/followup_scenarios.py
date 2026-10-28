"""Read-only: the W1/W10 follow-up matrix through the real API, in the citizen page's order (CitizenPage.answerFollowUp):
identify the follow-up; a procedure it names answers it; otherwise the open page, then a matched page if that abstains.
Since 27 Oct 2026 (remaining identification failures) the citizen page moves to that matched page only when it
answers; when it abstains too, the open page and its reply stay, and so here.
DATABASE_URL picks the database. Writes nothing."""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app

c = TestClient(app)
CASES = [  # (id, open page, follow-up, expected final page(s), note)
    ("A1", 36, "What about EPS?", [37], "switch; no EPF fact as EPS"),
    ("A2", 36, "How do I claim EDLI insurance?", [38], "switch"),
    ("A3", 22, "How do I register to vote?", [19], "switch"),
    ("A4", 15, "And what about linking PAN with Aadhaar?", [31], "switch"),
    ("A5", 19, "What about voters living abroad?", [21], "switch via fallback"),
    ("X2", 36, "How much of my employer's share goes to EPS?", [37, 36], "either"),
    ("B1", 26, "And how much does it cost?", [26], "stay; Rs. 1000 from the fee table, no other rows"),
    ("B2", 23, "What documents are required?", [23], "stay"),
    ("B3", 36, "What is the eligibility?", [36], "stay"),
    ("B4", 15, "What about the application process?", [15], "stay"),
    ("B5", 24, "Can I do it online?", [24], "stay"),
    ("B6", 30, "What if the owner died?", [30], "stay"),
    ("C1", 36, "What about the pension?", [36], "stay; no EPF fact as EPS"),
    ("C2", 24, "What is the fee?", [24], "stay; completion from 27 allowed"),
    ("C3", 28, "What about the certificate?", [28], "stay; never page 17"),
    ("C4", 18, "Can I do this at a post office?", [18, 35], "stay, or 35 if confident"),
    ("X1", 36, "Is EPS part of EPF?", [36], "stay (names both)"),
]
for cid, open_page, q, expected, note in CASES:
    ident = c.post("/api/identify", json={"question": q, "language": "en"}).json()
    other = ident["candidates"][0]["id"] if ident.get("status") == "matched" and ident["candidates"][0]["id"] != open_page else None
    target = other if other and ident.get("named") else open_page
    reply = c.post("/api/guidance", json={"procedure_id": target, "question": q, "language": "en"}).json()
    if reply["insufficient_evidence"] and other and target != other:
        second = c.post("/api/guidance", json={"procedure_id": other, "question": q, "language": "en"}).json()
        if not second["insufficient_evidence"]:
            target, reply = other, second
    claims = [(cl.get("procedure_id", target), cl["text"][:150]) for cl in reply["claims"]]
    print(json.dumps({"id": cid, "open": open_page, "q": q, "identify": [ident.get("status"), other, ident.get("named", False)],
                      "final_page": target, "page_ok": target in expected, "expected": expected, "note": note,
                      "outcome": "abstained" if reply["insufficient_evidence"] else f"{len(claims)} claims{' partial' if reply.get('partial') else ''}",
                      "claims": claims}, ensure_ascii=False), flush=True)
