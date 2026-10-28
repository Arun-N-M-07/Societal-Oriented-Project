"""Read-only check that the approved database matches the reviewed migration plan (07, "Proposed migration";
19_MASTER_RELIABILITY_EXECUTION.md, P0-3). Run it after the migration, and before it to see what still differs:
    .venv/bin/python PROCEDUREASSIST_HANDOFF/evidence/other/scripts/validate_migration.py [--embeddings]
DATABASE_URL picks the database to check (default: the app's); it may not be procedureassist_staging, which is the
reference: its text, chunks and cards are what the migration must reproduce, apart from the reviewer's corrections
below. Both sessions are read-only transactions; nothing is written. --embeddings also re-embeds every chunk (Ollama)
and compares it with the stored vector. Exit code 1 if any check fails."""
import math, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from backend.config import DATABASE_URL, EMBEDDING_DIMENSIONS
from backend.models import Procedure, ProcedureChunk
from backend.rag import chunk_text

REFERENCE = "procedureassist_staging"
FIELDS = ("name", "department", "jurisdiction", "summary", "eligibility", "steps")
# The reviewer's corrections (19, "P0-3"; 07). Every other card field of every page must equal the reference record.
# 27 Oct 2026: page 17 is deleted, not replaced (owner decision), so it has no entry and must not be stored; page 39's
# step is the owner's wording. Further corrections proposed for the owner (p9_final/replacement_field_review.md) are added
# here only once approved.
REVIEWED = {
    "https://parivahan.gov.in/en/content/fees-and-user-charges": {
        "name": "Vehicle Registration Fees and User Charges",
        "department": "Ministry of Road Transport and Highways (Parivahan)",
        "steps": ["Refer to the fee table to identify the applicable fee for the relevant vehicle-related service."],
    },
    "https://www.pfrda.org.in/schemes/atal-pension-yojana-apy": {
        "eligibility": "All Indian citizens with savings bank accounts in banks or Department of Posts, aged between 18 and "
                       "40 years. From 1st October, 2022, any citizen who is or has been an income-tax payer is not eligible "
                       "to join APY.",
    },
}


def load(session: Session) -> tuple[dict, int]:
    """{source_url: page} with card fields, text and (index, content, vector) chunks; and the orphan chunk count."""
    session.execute(text("SET TRANSACTION READ ONLY"))
    pages = {}
    for p in session.query(Procedure):
        chunks = session.query(ProcedureChunk).filter_by(procedure_id=p.id).order_by(ProcedureChunk.chunk_index).all()
        pages[p.source_url] = {
            "id": p.id, "name": p.name, "department": p.department, "jurisdiction": p.jurisdiction, "summary": p.summary,
            "eligibility": (p.structured_data or {}).get("eligibility"), "steps": (p.structured_data or {}).get("steps"),
            "text": p.source_text, "chunks": [(c.chunk_index, c.content, list(c.embedding)) for c in chunks],
        }
    orphans = session.query(ProcedureChunk).filter(~ProcedureChunk.procedure_id.in_(session.query(Procedure.id))).count()
    return pages, orphans


def valid_vector(vector) -> bool:
    return (len(vector) == EMBEDDING_DIMENSIONS and all(math.isfinite(v) for v in vector)
            and math.sqrt(sum(v * v for v in vector)) > 0)


def faq_pairs(source_text: str) -> list[tuple[str, str]]:
    """Each question paragraph with the paragraph after it ("" at the end)."""
    blocks = source_text.split("\n\n")
    return [(b, blocks[i + 1] if i + 1 < len(blocks) else "") for i, b in enumerate(blocks) if b.endswith("?")]


def validate(pages: dict, orphans: int, reference: dict, embed=None) -> list[str]:
    """Every failed check, printed as it runs. embed: a function giving fresh vectors (only with --embeddings)."""
    failures = []

    def check(ok, what):
        print(f"{'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            failures.append(what)

    check(len(pages) == len(reference), f"{len(reference)} pages, as the reference (found {len(pages)})")
    check(set(pages) == set(reference), f"same URLs as the reference (missing {sorted(set(reference) - set(pages))}, "
                                        f"extra {sorted(set(pages) - set(reference))})")
    total, expected_total = sum(len(p["chunks"]) for p in pages.values()), sum(len(p["chunks"]) for p in reference.values())
    check(total == expected_total, f"{expected_total} chunks in all (found {total})")
    check(orphans == 0, f"no orphan chunks (found {orphans})")
    for url, page in sorted(pages.items(), key=lambda item: item[1]["id"]):
        label = f"{page['name']} ({url})"
        ref = reference.get(url)
        if ref:
            check(page["text"] == ref["text"], f"text equals the reviewed reference text: {label}")
            expected = {**{f: ref[f] for f in FIELDS}, **REVIEWED.get(url, {})}
            for field in FIELDS:
                check(page[field] == expected[field], f"{field} as reviewed: {label}"
                      + ("" if page[field] == expected[field] else f" (found {page[field]!r}, expected {expected[field]!r})"))
            # A question keeps its own answer, in the same order; an answer is never another question (only the
            # "Have any questions?" heading is followed by a question).
            pairs = faq_pairs(page["text"])
            check(pairs == faq_pairs(ref["text"]) and all(
                answer.strip() and (not answer.endswith("?") or question == "Have any questions?") for question, answer in pairs),
                f"questions each followed by their own answer (found {len(pairs)}, reference {len(faq_pairs(ref['text']))}): {label}")
        chunks = page["chunks"]
        check([i for i, _, _ in chunks] == list(range(len(chunks))), f"chunk indexes 0..n-1: {label}")
        check([c for _, c, _ in chunks] == chunk_text(page["text"]), f"chunks equal chunk_text(source_text): {label}")
        check(all(valid_vector(v) for _, _, v in chunks), f"stored vectors: {EMBEDDING_DIMENSIONS} finite values, not zero: {label}")
        if embed and chunks:
            fresh = embed([c for _, c, _ in chunks])
            ok = len(fresh) == len(chunks) and all(valid_vector(f) for f in fresh) and all(valid_vector(v) for _, _, v in chunks)
            check(ok, f"fresh embeddings: one valid vector per chunk: {label}")
            if ok:
                cosine = lambda a, b: sum(x * y for x, y in zip(a, b)) / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
                check(min(cosine(v, f) for (_, _, v), f in zip(chunks, fresh)) > 0.9999, f"stored embeddings are current: {label}")
    return failures


if __name__ == "__main__":
    target = create_engine(DATABASE_URL)
    if target.url.database == REFERENCE:
        target.dispose()
        sys.exit(f"Refusing to validate {REFERENCE}: it is the reference, not the migrated database.")
    reference_engine = create_engine(DATABASE_URL.rsplit("/", 1)[0] + "/" + REFERENCE)
    try:
        with Session(target) as db, Session(reference_engine) as ref_db:
            pages, orphans = load(db)
            reference, _ = load(ref_db)
            db.rollback()
            ref_db.rollback()
    finally:
        target.dispose()
        reference_engine.dispose()
    embed = None
    if "--embeddings" in sys.argv:
        from backend.rag import embed_texts
        embed = embed_texts
    failures = validate(pages, orphans, reference, embed)
    print(f"\n{len(failures)} failed check(s)")
    sys.exit(1 if failures else 0)
