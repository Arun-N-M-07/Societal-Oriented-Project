"""Read-only: cosine similarity of every page-39 chunk for RC fee questions, plus what each chunk is about."""
import re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from sqlalchemy import text
from backend import rag
from backend.database import SessionLocal
QS = ["What is the fee to renew my vehicle RC?", "What is the fee to renew the RC of a motorcycle?",
      "What is the fee to renew the registration certificate of my motorcycle?", "RC renewal fee for a car",
      "What is the fitness test fee for a motorcycle?", "How much does a duplicate RC cost?"]
with SessionLocal() as db:
    rows = db.execute(text("select id, content from procedure_chunks where procedure_id=39 order by chunk_index")).all()
    def topic(content):
        items = sorted({m.group(1) for m in re.finditer(r"^(\d+)\.", content, re.M)}, key=int)
        return f"items {','.join(items)}"
    for q in QS:
        v = rag.embed_texts([q], query=True)[0]
        scored = db.execute(text("select id, 1 - (embedding <=> cast(:v as vector)) from procedure_chunks where procedure_id=39 order by 2 desc"),
                            {"v": str(v)}).all()
        print(f"\n## {q}")
        for rank, (cid, s) in enumerate(scored, 1):
            content = next(c for i, c in rows if i == cid)
            print(f"  {rank:2}. chunk {cid} {s:.3f} {topic(content):18} {'<- RC renewal rows' if cid in (588, 589, 590, 591) else ''}")
