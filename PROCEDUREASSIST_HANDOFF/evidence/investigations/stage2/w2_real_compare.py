"""Read-only: implemented _decide vs the old behaviour (own=True ignored), whole message, staging, embeddings only."""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
from backend import procedure_search as ps
from backend.database import SessionLocal
from backend.models import Procedure
root = "/Users/arunnm/Projects/SOP/fixtures/evaluation/"
msgs = [(f, c["message"]) for f in ("answers", "heldout", "multi_need", "population", "demo_services")
        for c in json.load(open(root + f + ".json"))["cases"] if c.get("language") != "ta"]
msgs += [("identification", q["question"]) for q in json.load(open(root + "identification.json"))["questions"]]
msgs += [("w2", q) for q in ["What is the fee to renew the RC of a motorcycle?", "How much does a duplicate RC cost?", "How do I renew my RC?",
         "RC renewal fee for a car", "What is the RC transfer fee?", "Is my RC valid in another state?", "What is RC?",
         "Can I withdraw my EPF?", "How much goes into EPS?", "What is the EDLI benefit?", "Can I renew my DL early?",
         "How do I get a duplicate DL?", "What is the DL renewal fee?", "How do I link PAN with Aadhaar?", "What is the fee for an IDP?"]]
real = ps.abbreviates
with SessionLocal() as db:
    names = {p.id: p.name for p in db.query(Procedure)}
    changed = 0
    for (src, m), v in zip(msgs, rag.embed_texts([m for _, m in msgs], query=True)):
        new = ps._decide(db, v, m)
        ps.abbreviates = lambda a, n, own=False: real(a, n)
        old = ps._decide(db, v, m)
        ps.abbreviates = real
        o, n = (old[0], [p.id for p in old[1]]), (new[0], [p.id for p in new[1]])
        if o != n:
            changed += 1
            print(f"[{src}] {m!r}\n   old {o} {[names[i] for i in o[1]]}\n   new {n} {[names[i] for i in n[1]]}")
    print(f"changed {changed}/{len(msgs)}")
