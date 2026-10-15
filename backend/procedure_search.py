from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import IDENTIFY_MARGIN, IDENTIFY_MIN_SCORE
from backend.models import Procedure, ProcedureChunk
from backend import rag


MAX_CANDIDATES = 3


def classify(
    ranked: list[tuple[int, float]],
    min_score: float = IDENTIFY_MIN_SCORE,
    margin: float = IDENTIFY_MARGIN,
) -> tuple[str, list[int]]:
    """Turn (procedure_id, score) pairs, best first, into an outcome.

    A procedure is plausible when it clears min_score and is within margin
    of the best score. One plausible procedure is a match; several need the
    citizen to choose; none means no reliable match.
    """
    if not ranked:
        return "no_match", []
    best = ranked[0][1]
    plausible = [
        procedure_id
        for procedure_id, score in ranked[:MAX_CANDIDATES]
        if score >= min_score and best - score <= margin
    ]
    if not plausible:
        return "no_match", []
    return ("matched" if len(plausible) == 1 else "ambiguous"), plausible


def rank_procedures(db: Session, question: str) -> list[tuple[int, float]]:
    """Score each procedure by its most similar evidence chunk, best first."""
    vector = rag.embed_texts([question], query=True)[0]
    score = func.max(1 - ProcedureChunk.embedding.cosine_distance(vector)).label("score")
    rows = (
        db.query(ProcedureChunk.procedure_id, score)
        .group_by(ProcedureChunk.procedure_id)
        .order_by(score.desc())
        .limit(MAX_CANDIDATES)
        .all()
    )
    return [(row.procedure_id, float(row.score)) for row in rows]


def identify(db: Session, question: str) -> tuple[str, list[Procedure]]:
    status, ids = classify(rank_procedures(db, question))
    found = {p.id: p for p in db.query(Procedure).filter(Procedure.id.in_(ids))}
    return status, [found[procedure_id] for procedure_id in ids]
