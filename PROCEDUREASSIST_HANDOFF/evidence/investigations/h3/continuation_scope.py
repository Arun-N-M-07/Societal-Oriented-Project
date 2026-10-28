"""Read-only: which retrievals the row-group continuation would change (fixture and audit-probe questions, expected
page), and which stored chunks could ever trigger it (a chunk ending with a numbered item continued by the next chunk)."""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
sys.path.insert(0, "/private/tmp/claude-501/-Users-arunnm-Projects-SOP/bebaf14e-7bdf-4da2-8b3f-9c2a6edb540d/scratchpad/h3")
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure, ProcedureChunk
from variants import continuation, ITEM
with SessionLocal() as db:
    pages = db.query(Procedure).all()
    print("== chunks that can trigger continuation (ends with a numbered item that the next chunk continues)")
    for p in pages:
        cs = db.query(ProcedureChunk).filter_by(procedure_id=p.id).order_by(ProcedureChunk.chunk_index).all()
        for a, b in zip(cs, cs[1:]):
            m = ITEM.match(a.content.split("\n\n")[-1])
            if m and b.content.startswith(m.group(1)):
                print(f"  page {p.id} chunk {a.id} -> {b.id}: {m.group(1)[:70]}")
    root = "/Users/arunnm/Projects/SOP/fixtures/evaluation/"
    qs = []
    for f in ("answers", "heldout"):
        for c in json.load(open(root + f + ".json"))["cases"]:
            frag = c.get("context") or (c.get("expected") or [None])[0]
            page = next((p for p in pages if isinstance(frag, str) and frag in p.source_url), None)
            if page and c.get("language") != "ta":
                qs.append((f, page.id, c["message"]))
    for l in open("/Users/arunnm/Projects/SOP/PROCEDUREASSIST_HANDOFF/evidence/investigations/rag_audit/probe_staging.jsonl"):
        r = json.loads(l)
        qs += [("probe", pid, r["q"]) for pid in r["expected"]]
    changed = 0
    print("\n== retrievals that change (question asked on its expected page)")
    for src, pid, q in qs:
        base = rag.retrieve(db, pid, q)
        more = continuation(db, base)[len(base):] if base else []
        if more:
            changed += 1
            print(f"  [{src}] page {pid} +{[c.id for c in more]}: {q[:80]}")
    print(f"  changed {changed}/{len(qs)}")
