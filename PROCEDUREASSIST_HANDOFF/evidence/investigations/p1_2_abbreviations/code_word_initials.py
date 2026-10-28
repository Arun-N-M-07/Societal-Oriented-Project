"""Read-only (embeddings only): does excluding code words ("REV-101") from a name's initials change any decision?
Today abbreviates("RC", "REV-101 Community Certificate") is True (initials R, C, C), so an RC question can be sent to
page 17 when it is the only nearby page with those initials. Every labelled question with a capitalised abbreviation
(w11_eval.load_cases, the safety set, and RC/DL/PF/EPS/PAN probes) is decided by procedure_search._decide with today's
abbreviates and with the variant; changes are printed. DATABASE_URL picks the database; nothing is written."""
import json, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
sys.path.insert(0, "/Users/arunnm/Projects/SOP/PROCEDUREASSIST_HANDOFF/evidence/investigations/w11")
from backend import rag, procedure_search as ps
from backend.database import SessionLocal
from backend.models import Procedure
from w11_eval import load_cases

today = ps.abbreviates
def variant(acronym, name, own=False):
    words = re.findall(r"\b[A-Z][\w'’-]*", name)
    if re.search(rf"\b{re.escape(acronym)}\b", name):
        return True
    initials = "".join(w[0] for w in words if not re.search(r"\d", w))
    return initials.startswith(acronym) if own else acronym in initials

with SessionLocal() as db:
    pages = db.query(Procedure).all()
    qs = [c[1] for c in load_cases(pages)]
    qs += [c["message"] for c in json.load(open("/Users/arunnm/Projects/SOP/fixtures/evaluation/safety.json"))["cases"]]
    qs += ["What about the RC?", "How do I renew my RC?", "What is the RC renewal fee?", "How do I transfer my RC?",
           "RC lost, how do I get a duplicate RC?", "Can I renew my DL online?", "What is the DL renewal fee?",
           "How do I withdraw my PF?", "What is EPS?", "How do I link my PAN?", "Is my PAN valid?"]
    qs = sorted({q for q in qs if ps.ACRONYM.search(q)})
    name = {p.id: p.name for p in pages}
    changed = 0
    for q, v in zip(qs, rag.embed_texts(qs, query=True)):
        ps.abbreviates = today; a = ps._decide(db, v, q)
        ps.abbreviates = variant; b = ps._decide(db, v, q)
        ps.abbreviates = today
        fa, fb = (a[0], [p.id for p in a[1]]), (b[0], [p.id for p in b[1]])
        if fa != fb:
            changed += 1
            print(f"CHANGED {q!r}: today {fa} -> variant {fb}")
    print(f"{len(qs)} questions with abbreviations; {changed} decisions change")
