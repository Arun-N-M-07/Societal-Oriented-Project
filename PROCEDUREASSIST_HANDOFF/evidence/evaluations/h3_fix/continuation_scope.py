"""Read-only: retrievals (fixture and audit-probe questions on their expected pages) where the implemented
rag.retrieve differs from the plain top-k query, i.e. where row-group continuation adds chunks."""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure
root = "/Users/arunnm/Projects/SOP/"
with SessionLocal() as db:
    pages = db.query(Procedure).all()
    qs = []
    for f in ("answers", "heldout"):
        for c in json.load(open(root + f"fixtures/evaluation/{f}.json"))["cases"]:
            frag = c.get("context") or (c.get("expected") or [None])[0]
            page = next((p for p in pages if isinstance(frag, str) and frag in p.source_url), None)
            if page and c.get("language") != "ta":
                qs.append((f, page.id, c["message"]))
    for l in open(root + "PROCEDUREASSIST_HANDOFF/evidence/investigations/rag_audit/probe_staging.jsonl"):
        r = json.loads(l)
        qs += [("probe", pid, r["q"]) for pid in r["expected"] if any(p.id == pid for p in pages)]
    changed = 0
    for src, pid, q in qs:
        full = rag.retrieve(db, pid, q)
        plain = full[:rag.GUIDANCE_PASSAGES] if len(full) > rag.GUIDANCE_PASSAGES else full
        extra = rag._item_continuation(db, plain, q)
        if extra:
            changed += 1
            print(f"  [{src}] page {pid} +{[c.id for c in extra]}: {q[:80]}")
    print(f"retrievals changed by continuation: {changed}/{len(qs)}")
