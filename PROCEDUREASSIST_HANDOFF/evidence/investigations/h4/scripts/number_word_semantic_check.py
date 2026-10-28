"""Read-only: do wrong numbers written in words survive verify_claims, and does the model's
check_claims catch them? Uses the real retrieved chunks; writes nothing. DATABASE_URL picks the DB."""
import os, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure

RUNS = 3
# (label, question, page URL fragment, claim text, quote copied from the official text, correct?)
CASES = [
    ("age control: 20 for transport", "At what age can I drive a transport vehicle?", "learners-license",
     "You can apply for a licence to drive a transport vehicle after completing twenty years of age.",
     "An applicant who has completed twenty years of age will be eligible for applying for a licence to drive a transport vehicle", True),
    ("age WRONG: 18 against a quote saying 20", "At what age can I drive a transport vehicle?", "learners-license",
     "You can apply for a licence to drive a transport vehicle after completing eighteen years of age.",
     "An applicant who has completed twenty years of age will be eligible for applying for a licence to drive a transport vehicle", False),
    ("age control: 18 for non-transport", "At what age can I get a driving licence?", "learners-license",
     "After completing eighteen years of age you can apply for a driving licence for a vehicle other than a transport vehicle.",
     "The applicant who has completed the age of eighteen years of age is eligible to apply for a driving licence to drive a motor vehicle other than a transport vehicle", True),
    ("age WRONG: 20 against a quote saying 18", "At what age can I get a driving licence?", "learners-license",
     "After completing twenty years of age you can apply for a driving licence for a vehicle other than a transport vehicle.",
     "The applicant who has completed the age of eighteen years of age is eligible to apply for a driving licence to drive a motor vehicle other than a transport vehicle", False),
    ("deadline control: three months", "How long can a legal heir use a vehicle after the owner dies?", "ownership-transfer",
     "The person succeeding to the possession of the vehicle may use it for a period of three months.",
     "the person succeeding to the possession of the vehicle may for a period of three months, use the vehicle", True),
    ("deadline WRONG: six months against three", "How long can a legal heir use a vehicle after the owner dies?", "ownership-transfer",
     "The person succeeding to the possession of the vehicle may use it for a period of six months.",
     "the person succeeding to the possession of the vehicle may for a period of three months, use the vehicle", False),
    ("deadline WRONG: thirty days against fourteen", "Within how many days must a buyer apply for ownership transfer of a vehicle registered in the same state?", "ownership-transfer",
     "For a vehicle registered within the same State, the buyer must apply for transfer of ownership within thirty days of the transfer.",
     "in the case of a vehicle registered within the same State, within fourteen days of the transfer, application for the transfer of ownership of a motor vehicle shall be made by the transferee", False),
    ("deadline WRONG: 30 (digits) against fourteen", "Within how many days must a buyer apply for ownership transfer of a vehicle registered in the same state?", "ownership-transfer",
     "For a vehicle registered within the same State, the buyer must apply for transfer of ownership within 30 days of the transfer.",
     "in the case of a vehicle registered within the same State, within fourteen days of the transfer, application for the transfer of ownership of a motor vehicle shall be made by the transferee", False),
    ("count WRONG: three copies against two", "How do I register as a voter?", "general-voters",
     "Fill three copies of Form 6.", "Fill two copies of Form 6", False),
]

print("DB:", os.environ.get("DATABASE_URL", "procedureassist (.env)").rsplit("/", 1)[-1])
with SessionLocal() as db:
    for label, question, url, text, quote, correct in CASES:
        page = db.query(Procedure).filter(Procedure.source_url.like(f"%{url}%")).one()
        chunks = rag.retrieve(db, page.id, question)
        holder = next((c for c in chunks if rag._words(quote) in rag._words(c.content)), None)
        print(f"\n## {label}  (official: {'correct' if correct else 'WRONG'})")
        if holder is None:
            print("   quote's chunk not among the retrieved chunks; skipped")
            continue
        claim = {"text": text, "quote": quote, "chunk_id": holder.id}
        kept = rag.verify_claims([claim], {c.id: c.content for c in chunks})
        print(f"   verify_claims (deterministic): {'KEPT' if kept else 'REJECTED'}")
        if not kept:
            continue
        results = []
        for _ in range(RUNS):
            checked, complete = rag.check_claims(question, kept, chunks)
            results.append("KEPT" if checked else "REJECTED")
        print(f"   check_claims (model) x{RUNS}: {results}")
        if not correct and "KEPT" in results:
            print("   >>> WRONG CLAIM REACHES THE CITIZEN")
