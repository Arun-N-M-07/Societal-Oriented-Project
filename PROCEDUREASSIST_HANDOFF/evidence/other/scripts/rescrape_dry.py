"""Dry run: re-scrape every stored URL (and candidate new URLs) with the current scraper. Writes nothing to the DB."""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend.database import SessionLocal
from backend.models import Procedure
from backend.rag import chunk_text
from backend.scraper import scrape_url
OUT = sys.argv[1]; extra = sys.argv[2:]
res = {}
with SessionLocal() as db:
    targets = [(p.id, p.source_url, p.source_text) for p in db.query(Procedure).order_by(Procedure.id)] + [(None, u, "") for u in extra]
for pid, url, old in targets:
    try:
        r = scrape_url(url); new = r.source_text
    except Exception as e:
        print(pid, url, "ERROR", e); continue
    ob, nb = old.split("\n\n"), new.split("\n\n")
    removed = [b for b in ob if b not in nb]; added = [b for b in nb if b not in ob]
    res[str(pid or url)] = {"id": pid, "url": url, "final": r.source_url, "text": new, "removed": removed, "added": added,
                            "chunks_old": len(chunk_text(old)) if old else 0, "chunks_new": len(chunk_text(new))}
    print(f"{pid} {url[:70]:70} chars {len(old)}->{len(new)} blocks -{len(removed)} +{len(added)} chunks {res[str(pid or url)]['chunks_old']}->{res[str(pid or url)]['chunks_new']}", flush=True)
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
