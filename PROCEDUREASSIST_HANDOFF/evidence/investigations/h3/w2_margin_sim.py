"""Read-only: current _decide vs two W2 variants, whole message, embeddings only.
  own-only : (withdrawn) a confident match yields only to the other page's own abbreviation
  margin   : (proposed) ... or to an abbreviation-named page within IDENTIFY_MARGIN of the best score"""
import json, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag, procedure_search as ps
from backend.config import IDENTIFY_MARGIN
from backend.database import SessionLocal
from backend.models import Procedure

def decide(db, vector, text, variant):
    ranked = ps.rank_procedures(db, vector)
    status, ids = ps.classify(ranked)
    score = dict(ranked)
    if acronyms := ps.ACRONYM.findall(text):
        near = [i for i, s in ranked if s >= ps.ACRONYM_MIN_SCORE]
        nearby = db.query(Procedure).filter(Procedure.id.in_(near)).all()
        named = [p.id for p in nearby if any(ps.abbreviates(a, p.name) for a in acronyms)]
        if not named and status != "matched":
            uses = lambda p: any(re.search(rf"\b{re.escape(a)}\b", p.source_text) for a in acronyms)
            named = [p.id for p in db.query(Procedure) if uses(p)]
            named = named if len(named) == 1 and named[0] in near else []
        if variant != "current" and status == "matched" and named and named != ids:
            own = lambda p: any(ps.abbreviates(a, p.name, own=True) for a in acronyms)
            close = lambda p: variant == "margin" and ranked[0][1] - score[p.id] <= IDENTIFY_MARGIN
            named = [p.id for p in nearby if p.id in named and (own(p) or close(p))]
        if len(named) == 1:
            status, ids = "matched", named
    found = {p.id: p for p in db.query(Procedure).filter(Procedure.id.in_(ids))}
    procedures = [found[i] for i in ids if ps.mentions(found[i].source_text, text)]
    if not procedures:
        return ("no_match", [])
    if status == "ambiguous" and len(procedures) == 1:
        return ("ambiguous", ids)
    if len(procedures) > 1 and (page := ps.named_by_the_others(text, procedures)):
        return ("matched", [page.id])
    return ("matched" if len(procedures) == 1 else "ambiguous", [p.id for p in procedures])

root = "/Users/arunnm/Projects/SOP/fixtures/evaluation/"
msgs = [(f, c["message"]) for f in ("answers", "heldout", "multi_need", "population", "demo_services")
        for c in json.load(open(root + f + ".json"))["cases"] if c.get("language") != "ta"]
msgs += [("identification", q["question"]) for q in json.load(open(root + "identification.json"))["questions"]]
msgs += [("probe", q) for q in ["When can I take out my whole PF money?", "How much PF does my employer pay?", "Can I withdraw my PF?",
         "What is the fee to renew the RC of a motorcycle?", "RC renewal fee for a car", "What is the fee to renew my vehicle RC?",
         "How much does a duplicate RC cost?", "How do I renew my RC?", "What documents are needed to renew my vehicle RC?",
         "Can I withdraw my EPF?", "How much goes into EPS?", "What is the EDLI benefit?", "Can I renew my DL early?",
         "What is the DL renewal fee?", "How do I link PAN with Aadhaar?", "What is the IDP fee?"]]
with SessionLocal() as db:
    names = {p.id: p.name[:34] for p in db.query(Procedure)}
    vectors = rag.embed_texts([m for _, m in msgs], query=True)
    diff = {"own-only": 0, "margin": 0}
    for (src, m), v in zip(msgs, vectors):
        cur, own, mar = (decide(db, v, m, k) for k in ("current", "own-only", "margin"))
        if (cur, own, mar) != (cur, cur, cur):
            diff["own-only"] += own != cur; diff["margin"] += mar != cur
            fmt = lambda r: f"{r[0]} {[names.get(i, i) for i in r[1]]}"
            print(f"[{src}] {m!r}\n   current  {fmt(cur)}\n   own-only {fmt(own)}\n   margin   {fmt(mar)}")
    print(f"changed vs current: own-only {diff['own-only']}, margin {diff['margin']} of {len(msgs)}")
