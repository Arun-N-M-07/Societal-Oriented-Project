"""Read-only: answers for page-39 fee questions under three retrieval variants (nothing is changed):
  top5     : rag.retrieve as today
  continue : top5 + following chunks that continue the numbered item a retrieved chunk ends with
  page     : every chunk of the page (upper bound)
Each answer goes through the real _answer (verify_claims) and check_claims."""
import re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
from backend.database import SessionLocal
from backend.models import ProcedureChunk

ITEM = re.compile(r"^(\d+\.\s[^:\n]{10,}):")  # "4. Issue or renewal of certificate of registration ...:"

def continuation(db, chunks):
    """Chunks that continue the numbered item each retrieved chunk ends with (same label at their start)."""
    page = db.query(ProcedureChunk).filter_by(procedure_id=chunks[0].procedure_id).order_by(ProcedureChunk.chunk_index).all()
    have = {c.id for c in chunks}; extra = []
    for c in chunks:
        label = ITEM.match(c.content.split("\n\n")[-1])
        if not label:
            continue
        for nxt in page[c.chunk_index + 1:]:
            if not nxt.content.startswith(label.group(1)):
                break
            if nxt.id not in have:
                have.add(nxt.id); extra.append(nxt)
    return chunks + extra

QS = [("What is the fee to renew my vehicle RC?", "RC renewal, no class: rows 4(a)-(j), not item 11/16"),
      ("What is the fee to renew the RC of a motorcycle?", "4(b) Rs 300"),
      ("What is the fee to renew the registration certificate of my motorcycle?", "4(b) Rs 300"),
      ("RC renewal fee for a car", "4(c)i Rs 600 (non-transport LMV)"),
      ("What is the RC renewal fee for a heavy goods vehicle?", "4(f) Rs 1500"),
      ("What is the fitness test fee for a motorcycle?", "10(a) manual 200 / automated 400"),
      ("What is the RC renewal fee for an imported car older than 20 years?", "item 16 (older than 20 years)"),
      ("How much does a duplicate RC cost?", "5: half of item 4")]
with SessionLocal() as db:
    for q, expect in QS:
        base = rag.retrieve(db, 39, q)
        variants = {"top5": base, "continue": continuation(db, base),
                    "page": db.query(ProcedureChunk).filter_by(procedure_id=39).order_by(ProcedureChunk.chunk_index).all()}
        print(f"\n## {q}   [expected: {expect}]")
        for name, chunks in variants.items():
            claims, omitted = rag._answer(q, chunks)
            kept, complete = rag.check_claims(q, claims, chunks) if claims else ([], False)
            print(f"  {name:8} chunks {sorted(c.id for c in chunks)} -> verified {len(claims)}, kept {len(kept)}, complete={complete}")
            for c in kept:
                print(f"      - {c['text'][:150]}")
