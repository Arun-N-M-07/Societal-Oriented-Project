"""Read-only: for every English fixture case with an expected page and evidence pattern, the rank of the
first chunk containing the evidence among that page's chunks ordered as retrieve() orders them.
Only pages with more than GUIDANCE_PASSAGES chunks can lose evidence at this step."""
import json, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure, ProcedureChunk
K = rag.GUIDANCE_PASSAGES
with SessionLocal() as db:
    pages = db.query(Procedure).all()
    counts = {p.id: db.query(ProcedureChunk).filter_by(procedure_id=p.id).count() for p in pages}
    rows = []
    for fx in ("answers", "heldout"):
        for i, c in enumerate(json.load(open(f"/Users/arunnm/Projects/SOP/fixtures/evaluation/{fx}.json"))["cases"]):
            exp, ev = c.get("expected") or [], c.get("evidence")
            if c.get("language") == "ta" or not ev or len(exp) != 1 or exp[0] in (None, "ambiguous"):
                continue
            page = next((p for p in pages if exp[0] in p.source_url), None)
            if page is None:
                continue
            ordered = rag.retrieve(db, page.id, c["message"], limit=counts[page.id])
            ranks = [r for r, ch in enumerate(ordered, 1) if re.search(ev, ch.content, re.I)]
            rows.append((fx, i, page.id, counts[page.id], ranks[0] if ranks else None, c["message"]))
    big = [r for r in rows if r[3] > K]
    print(f"cases checked: {len(rows)}; on pages with more than {K} chunks: {len(big)}")
    print(f"evidence chunk within top {K}: {sum(1 for r in rows if r[4] and r[4] <= K)}/{len(rows)}; not stored on page: {sum(1 for r in rows if r[4] is None)}")
    for fx, i, pid, n, rank, msg in sorted(big, key=lambda r: -(r[4] or 99)):
        print(f"  {fx}[{i}] page {pid} ({n} chunks) evidence rank {rank}: {msg[:80]}")
    for fx, i, pid, n, rank, msg in rows:
        if rank is None:
            print(f"  NOT STORED {fx}[{i}] page {pid}: {msg[:80]}")
