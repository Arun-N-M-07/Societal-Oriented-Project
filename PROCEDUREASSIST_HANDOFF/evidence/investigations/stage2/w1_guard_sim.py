"""Read-only simulation of a proposed W1 guard (nothing is changed): /api/guidance would decline when the question
names another procedure (an abbreviation of its name, or every word of its name) and does not name the requested one.
Reuses procedure_search.abbreviates and the name-word test of named_by_the_others. No model calls."""
import json, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend.database import SessionLocal
from backend.models import Procedure
from backend.procedure_search import abbreviates, ACRONYM, NAME_STOP_WORDS

def names(question, page):
    asked = re.findall(r"\w+", question.lower())
    words = [w for w in re.findall(r"\w+", page.name.lower()) if w not in NAME_STOP_WORDS]
    return any(abbreviates(a, page.name) for a in ACRONYM.findall(question)) or all(any(x.startswith(w[:5]) for x in asked) for w in words)

def fires(question, target, pages):
    others = [p for p in pages if p.id != target.id and names(question, p)]
    return [p.id for p in others] if others and not names(question, target) else []

with SessionLocal() as db:
    pages = db.query(Procedure).all()
    by_url = lambda frag: next((p for p in pages if frag in p.source_url), None)
    print("== fixture cases: target = context page (follow-ups) or the expected page")
    n = hit = 0
    for fx in ("answers", "heldout"):
        for i, c in enumerate(json.load(open(f"/Users/arunnm/Projects/SOP/fixtures/evaluation/{fx}.json"))["cases"]):
            frag = c.get("context") or ((c.get("expected") or [None])[0])
            target = by_url(frag) if isinstance(frag, str) and frag != "ambiguous" else None
            if target is None or c.get("language") == "ta":
                continue
            n += 1
            f = fires(c["message"], target, pages)
            if f:
                hit += 1
                print(f"  FIRES {fx}[{i}] target {target.id} names {f}: {c['message']}")
    print(f"  fired on {hit}/{n} English fixture cases")
    print("== W1 follow-up cases (target = open page)")
    for cid, open_page, q in [("A1", 36, "What about EPS?"), ("A2", 36, "How do I claim EDLI insurance?"), ("A3", 22, "How do I register to vote?"),
                              ("A4", 15, "And what about linking PAN with Aadhaar?"), ("A5", 19, "What about voters living abroad?"),
                              ("B1", 26, "And how much does it cost?"), ("B2", 23, "What documents are required?"), ("B3", 36, "What is the eligibility?"),
                              ("B4", 15, "What about the application process?"), ("B5", 24, "Can I do it online?"), ("B6", 30, "What if the owner died?"),
                              ("C1", 36, "What about the pension?"), ("C2", 24, "What is the fee?"), ("C3", 28, "What about the certificate?"),
                              ("C4", 18, "Can I do this at a post office?"), ("X1", 36, "Is EPS part of EPF?"), ("X2", 36, "How much of my employer's share goes to EPS?")]:
        target = next(p for p in pages if p.id == open_page)
        print(f"  {cid} open {open_page}: guard {'FIRES -> names ' + str(fires(q, target, pages)) if fires(q, target, pages) else 'silent'} | {q}")
