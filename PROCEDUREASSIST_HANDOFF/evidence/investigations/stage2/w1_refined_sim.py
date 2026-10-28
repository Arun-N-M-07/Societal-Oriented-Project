"""Read-only: the refined W1 rule on every fixture follow-up and the W1 cases. Switch only if the follow-up names
procedure Y (abbreviation or all name words) AND /api/identify on the follow-up alone matched Y, and Y != open page."""
import json, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Procedure
from backend.procedure_search import abbreviates, ACRONYM, NAME_STOP_WORDS
c = TestClient(app)
def names(question, page):
    asked = re.findall(r"\w+", question.lower())
    words = [w for w in re.findall(r"\w+", page.name.lower()) if w not in NAME_STOP_WORDS]
    return any(abbreviates(a, page.name) for a in ACRONYM.findall(question)) or all(any(x.startswith(w[:5]) for x in asked) for w in words)
with SessionLocal() as db:
    pages = {p.id: p for p in db.query(Procedure)}
    cases = []
    for fx in ("answers", "heldout"):
        for i, cs in enumerate(json.load(open(f"/Users/arunnm/Projects/SOP/fixtures/evaluation/{fx}.json"))["cases"]):
            if "context" in cs:
                open_page = next(p for p in pages.values() if cs["context"] in p.source_url).id
                cases.append((f"{fx}[{i}]", open_page, cs["message"], cs.get("language", "en"), f"expected {cs['expected']}"))
    cases += [("A1", 36, "What about EPS?", "en", "switch 37"), ("A2", 36, "How do I claim EDLI insurance?", "en", "switch 38"),
              ("A3", 22, "How do I register to vote?", "en", "switch 19"), ("A4", 15, "And what about linking PAN with Aadhaar?", "en", "switch 31"),
              ("C1", 36, "What about the pension?", "en", "stay/ask"), ("C3", 28, "What about the certificate?", "en", "stay"),
              ("X1", 36, "Is EPS part of EPF?", "en", "stay (names both)"), ("X2", 36, "How much of my employer's share goes to EPS?", "en", "either")]
    for cid, open_page, q, lang, expect in cases:
        r = c.post("/api/identify", json={"question": q, "language": lang}).json()
        y = r["candidates"][0]["id"] if r.get("status") == "matched" else None
        query = r.get("normalized_query", q)
        switch = y is not None and y != open_page and names(query, pages[y])
        print(f"{cid:12} open {open_page:>2} identify={r.get('status')}:{y} names(y)={names(query, pages[y]) if y else '-'} -> {'SWITCH to ' + str(y) if switch else 'no early switch'} | {expect} | {q}")
