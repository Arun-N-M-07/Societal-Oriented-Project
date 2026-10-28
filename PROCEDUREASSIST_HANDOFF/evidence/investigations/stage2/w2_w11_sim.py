"""Read-only (embeddings only, no generation, no writes).
W2: _decide as implemented vs a proposed variant in which an abbreviation may override an already-confident
match only when it is the other page's own name (literal in the name, or the start of its initials).
W11: top page score of every out-of-scope question, against IDENTIFY_MIN_SCORE."""
import json, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
from backend import procedure_search as ps
from backend.config import IDENTIFY_MIN_SCORE
from backend.database import SessionLocal
from backend.models import Procedure

def own_name(acronym, name):
    initials = "".join(w[0] for w in re.findall(r"\b[A-Z][\w'’-]*", name))
    return bool(re.search(rf"\b{re.escape(acronym)}\b", name)) or initials.startswith(acronym)

def decide_new(db, vector, text):
    """Copy of procedure_search._decide with one added condition (marked)."""
    ranked = ps.rank_procedures(db, vector)
    status, ids = ps.classify(ranked)
    if acronyms := ps.ACRONYM.findall(text):
        near = [i for i, s in ranked if s >= ps.ACRONYM_MIN_SCORE]
        nearby = db.query(Procedure).filter(Procedure.id.in_(near)).all()
        named = [p.id for p in nearby if any(ps.abbreviates(a, p.name) for a in acronyms)]
        if not named and status != "matched":
            uses = lambda p: any(re.search(rf"\b{re.escape(a)}\b", p.source_text) for a in acronyms)
            named = [p.id for p in db.query(Procedure) if uses(p)]
            named = named if len(named) == 1 and named[0] in near else []
        # PROPOSED: a confident match is overridden only by the other page's own name
        if len(named) == 1 and status == "matched" and named != ids:
            page = next(p for p in nearby if p.id == named[0])
            if not any(own_name(a, page.name) for a in acronyms):
                named = []
        if len(named) == 1:
            status, ids = "matched", named
    found = {p.id: p for p in db.query(Procedure).filter(Procedure.id.in_(ids))}
    procedures = [found[i] for i in ids if ps.mentions(found[i].source_text, text)]
    if not procedures:
        return "no_match", []
    if status == "ambiguous" and len(procedures) == 1:
        return "ambiguous", [found[i] for i in ids]
    if len(procedures) > 1 and (page := ps.named_by_the_others(text, procedures)):
        return "matched", [page]
    return ("matched" if len(procedures) == 1 else "ambiguous"), procedures

root = "/Users/arunnm/Projects/SOP/fixtures/evaluation/"
msgs = []
for f in ("answers", "heldout", "multi_need", "population", "demo_services"):
    for c in json.load(open(root + f + ".json"))["cases"]:
        if c.get("language") != "ta":
            msgs.append((f, c["message"]))
ident = json.load(open(root + "identification.json"))["questions"]
msgs += [("identification", q["question"]) for q in ident]
msgs += [("w2", q) for q in ["What is the fee to renew the RC of a motorcycle?", "How much does a duplicate RC cost?",
         "How do I renew my RC?", "What documents are needed to renew my vehicle RC?", "RC renewal fee for a car",
         "What is the RC transfer fee?", "Can I withdraw my EPF?", "How much goes into EPS?", "What is the EDLI benefit?",
         "Can I renew my DL early?", "How do I get a duplicate DL?", "What is the DL renewal fee?", "How do I link PAN with Aadhaar?",
         "What is RC?", "Is my RC valid in another state?"]]
with SessionLocal() as db:
    names = {p.id: p.name for p in db.query(Procedure)}
    vectors = rag.embed_texts([m for _, m in msgs], query=True)
    changed = 0
    print("== W2: messages whose _decide outcome changes (whole message only; the full identify() flow is not replayed)")
    for (src, m), v in zip(msgs, vectors):
        old, new = ps._decide(db, v, m), decide_new(db, v, m)
        o, n = (old[0], [p.id for p in old[1]]), (new[0], [p.id for p in new[1]])
        if o != n:
            changed += 1
            print(f"  [{src}] {m!r}\n     now {o} {[names[i] for i in o[1]]}\n     new {n} {[names[i] for i in n[1]]}")
    print(f"  changed: {changed}/{len(msgs)}")
    print("\n== W11: out-of-scope questions (identification.json questions without an expected procedure, plus fixture outside cases)")
    outside = [q["question"] for q in ident if not q.get("expected") and not q.get("procedure")]
    for f in ("answers", "heldout"):
        outside += [c["message"] for c in json.load(open(root + f + ".json"))["cases"] if c.get("expected") == [None]]
    for q, v in zip(outside, rag.embed_texts(outside, query=True)):
        r = ps.rank_procedures(db, v)
        print(f"  top {r[0][1]:.3f} ({names[r[0][0]][:30]})  {'ABOVE' if r[0][1] >= IDENTIFY_MIN_SCORE else 'below'} {IDENTIFY_MIN_SCORE}  | {q}")
    print("  identification.json keys of a question:", list(ident[0]))
