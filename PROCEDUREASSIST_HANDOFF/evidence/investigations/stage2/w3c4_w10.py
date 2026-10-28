"""Read-only: (1) does the C4 wrong-deadline claim survive check_claims with the real retrieved chunks?
(2) W10: where 'as prescribed' appears, what check_claims says about it, and what answer_from_naming_pages returns."""
import subprocess, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure
with SessionLocal() as db:
    q = "Within how many days must a buyer apply for ownership transfer of a vehicle registered in the same state?"
    chunks = rag.retrieve(db, 30, q)
    quote = "in the case of a vehicle registered within the same State, within fourteen days of the transfer, application for the transfer of ownership of a motor vehicle shall be made by the transferee in Form 30"
    holder = next((c for c in chunks if rag._words(quote) in rag._words(c.content)), None)
    print("== C4: retrieved", [c.id for c in chunks], "quote in chunk", holder.id if holder else None)
    if holder:
        for text in ["For a vehicle registered within the same State, the buyer must apply within thirty days of the transfer in Form 30.",
                     "For a vehicle registered within the same State, the buyer must apply within fourteen days of the transfer in Form 30."]:
            kept = rag.verify_claims([{"text": text, "quote": quote, "chunk_id": holder.id}], {c.id: c.content for c in chunks})
            runs = [("KEPT" if rag.check_claims(q, kept, chunks)[0] else "REJECTED") for _ in range(3)] if kept else []
            print(f"  verify_claims {'KEPT' if kept else 'REJECTED'}; check_claims x3 {runs} :: {text}")
    print("\n== W10: pages whose stored text says 'as prescribed'")
    for p in db.query(Procedure).order_by(Procedure.id):
        for block in p.source_text.split("\n\n"):
            if "as prescribed" in block.lower():
                print(f"  page {p.id} {p.name}: {block[:120]!r}")
    print("\n== W10: IDP page (26), follow-up 'And how much does it cost?'")
    for question in ["And how much does it cost?", "What is the fee for an International Driving Permit?"]:
        ch = rag.retrieve(db, 26, question)
        claims, omitted = rag._answer(question, ch)
        checked, complete = rag.check_claims(question, claims, ch) if claims else ([], False)
        print(f"  [{question}] generated+verified: {[c['text'] for c in claims]} | check_claims kept {len(checked)} complete={complete}")
        related = rag.answer_from_naming_pages(db, db.get(Procedure, 26), question)
        print(f"     answer_from_naming_pages -> {(related[0].id, [c['text'] for c in related[1]], 'complete' if related[3] else 'incomplete') if related else None}")
