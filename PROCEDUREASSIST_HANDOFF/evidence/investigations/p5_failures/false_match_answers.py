"""Read-only: what the real /api/guidance answers for each question that the fixed identification still matches to an
unrelated page (the residual false matches of screen.py's ALLask), on the page it is matched to. The citizen page shows
the card of a procedure the citizen did not name only with an answer, so each must abstain to end as an abstention.
DATABASE_URL picks the database."""
import sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import routes
from backend.database import SessionLocal
from backend.schemas import GuidanceRequest
CASES = [("How do I get a marriage certificate?", 17), ("How do I apply for a marriage certificate?", 17),
         ("Where do I get a marriage certificate in Tamil Nadu?", 17), ("How do I get a birth certificate in Tamil Nadu?", 17),
         ("How do I change the name on my PAN card?", 32), ("How do I correct the spelling of my name on my PAN card?", 32),
         ("How do I apply for a new PAN card?", 32), ("How do I reprint my PAN card?", 32),
         ("What is the fee to apply for a PAN card?", 31)]
with SessionLocal() as db:
    for question, page in CASES:
        reply = routes.guidance(GuidanceRequest(procedure_id=page, question=question), db=db)
        print(f"{'ABSTAINED' if reply.insufficient_evidence else 'ANSWERED '} page {page}: {question}")
        for claim in reply.claims:
            print(f"     claim: {claim.text[:150]} | quote: {claim.quote[:100]}")
