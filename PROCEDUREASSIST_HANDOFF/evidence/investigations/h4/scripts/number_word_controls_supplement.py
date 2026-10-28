"""Read-only supplement to number_word_semantic_check.py: the two correct controls it lacked
(fourteen days, two copies). Same steps: real retrieval, verify_claims, check_claims x3. Writes nothing."""
import os, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure
CASES = [
    ("deadline control: fourteen days", "Within how many days must a buyer apply for ownership transfer of a vehicle registered in the same state?", "ownership-transfer",
     "For a vehicle registered within the same State, the buyer must apply for transfer of ownership within fourteen days of the transfer.",
     "in the case of a vehicle registered within the same State, within fourteen days of the transfer, application for the transfer of ownership of a motor vehicle shall be made by the transferee"),
    ("count control: two copies", "How do I register as a voter?", "general-voters", "Fill two copies of Form 6.", "Fill two copies of Form 6"),
]
print("DB:", os.environ.get("DATABASE_URL", "procedureassist (.env)").rsplit("/", 1)[-1])
with SessionLocal() as db:
    for label, question, url, text, quote in CASES:
        page = db.query(Procedure).filter(Procedure.source_url.like(f"%{url}%")).one()
        chunks = rag.retrieve(db, page.id, question)
        holder = next((c for c in chunks if rag._words(quote) in rag._words(c.content)), None)
        print(f"\n## {label}  (official: correct)")
        if holder is None:
            print("   quote's chunk not among the retrieved chunks; skipped"); continue
        kept = rag.verify_claims([{"text": text, "quote": quote, "chunk_id": holder.id}], {c.id: c.content for c in chunks})
        print(f"   retrieved chunk {holder.id}; verify_claims (deterministic): {'KEPT' if kept else 'REJECTED'}")
        if kept:
            print(f"   check_claims (model) x3: {['KEPT' if rag.check_claims(question, kept, chunks)[0] else 'REJECTED' for _ in range(3)]}")
