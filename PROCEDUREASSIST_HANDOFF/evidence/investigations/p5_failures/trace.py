"""Read-only trace of the real /api/identify path (routes.identify_procedure) for the questions that still fail.
The application code runs unchanged; thin wrappers only record what each step received and returned:
names_something, the multi-need gate and the model's need extraction, every text _decide is given (its top three
pages and scores, classify's outcome, the abbreviation override, mentions and covers for each candidate), and the
final status, candidates and named flag. Also prints where the expected page ranks among all pages.
Nothing is written to any database. DATABASE_URL picks the database.
    trace.py [question ...]   (default: the failing questions of the remaining-failures brief)"""
import os, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from sqlalchemy import func
from backend import procedure_search as ps, rag, routes
from backend.database import SessionLocal
from backend.models import Procedure, ProcedureChunk
from backend.schemas import IdentifyRequest

DB = os.environ.get("DATABASE_URL", "procedureassist").rsplit("/", 1)[-1]
QUESTIONS = [
    ("How do I get a marriage certificate?", None),
    ("How do I apply for a marriage certificate?", None),
    ("How do I register my marriage in Tamil Nadu?", None),
    ("How do I change the name on my PAN card?", None),
    ("How do I correct the spelling of my name on my PAN card?", None),
    ("How do I apply for a new PAN card?", None),
    ("how do i renew my uk driving licence", None),
    ("How do I apply for a certificate in Tamil Nadu?", None),
    ("I work in Dubai. Can I vote in India?", "overseas-voters"),
    ("I live abroad. How do I register to vote?", "overseas-voters"),
    ("sold my bike, need to transfer the RC", "ownership-transfer"),
    ("How much does a duplicate RC cost?", "fees-and-user-charges"),
    ("How much do I pay to get my DL renewed?", "content/renewal"),
    ("I sold my bike. What does the buyer have to do and by when?", "ownership-transfer"),
]
log = []

def wrap(module, name, show):
    real = getattr(module, name)
    def recorded(*args, **kwargs):
        result = real(*args, **kwargs)
        log.append(show(args, result))
        return result
    setattr(module, name, recorded)

with SessionLocal() as db:
    pages = {p.id: p for p in db.query(Procedure)}
    short = lambda i: f"{i}:{pages[i].name[:28]}"
    wrap(routes, "names_something", lambda a, r: f"  names_something -> {r}")
    wrap(ps, "extract_needs", lambda a, r: f"  extract_needs (multi-need gate passed) -> {r}")
    wrap(ps, "rank_procedures", lambda a, r: "      ranked " + ", ".join(f"{short(i)} {s:.3f}" for i, s in r))
    wrap(ps, "classify", lambda a, r: f"      classify -> {r}")
    wrap(ps, "mentions", lambda a, r: f"      mentions({short(next(i for i, p in pages.items() if p.source_text == a[0]))}) -> {r}")
    wrap(ps, "covers", lambda a, r: f"      covers({a[0]!r}) -> {r}")
    real_decide = ps._decide
    def decide(db_, vector, text, context=None, message=None):
        log.append(f"    _decide({text!r}" + (f", context={context!r})" if context else ")"))
        status, found = real_decide(db_, vector, text, context, message)
        log.append(f"    => {status} {[short(p.id) for p in found]}")
        return status, found
    ps._decide = decide
    asked = [(q, None) for q in sys.argv[1:]] or QUESTIONS
    print(f"### {DB}")
    for question, expected in asked:
        log.clear()
        reply = routes.identify_procedure(IdentifyRequest(question=question), db=db)
        print(f"\n## {question!r}" + (f"  (expected page: {expected})" if expected else ""))
        print("\n".join(log))
        print(f"  RESULT status={reply.status} candidates={[short(c.id) for c in reply.candidates]} "
              f"named={reply.named} clarification={reply.clarification!r}")
        if expected:
            [vector] = rag.embed_texts([question], query=True)
            score = func.max(1 - ProcedureChunk.embedding.cosine_distance(vector)).label("s")
            ranks = db.query(ProcedureChunk.procedure_id, score).group_by(ProcedureChunk.procedure_id).order_by(score.desc()).all()
            for n, row in enumerate(ranks, 1):
                if expected in pages[row.procedure_id].source_url:
                    print(f"  expected page {short(row.procedure_id)}: rank {n} of {len(ranks)}, whole-message score {row.s:.3f}")
