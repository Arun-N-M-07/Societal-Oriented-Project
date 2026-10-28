"""Read-only: chunker invariance and where old vs new _section_heading differ, both DBs."""
import sys; sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from sqlalchemy import create_engine, text
from backend.config import DATABASE_URL
import backend.rag as rag
def old(passage, quote):
    blocks = passage.split("\n\n")
    at = next((i for i, block in enumerate(blocks) if rag._words(quote) in rag._words(block)), None)
    return next((blocks[i] for i in range(at, -1, -1) if rag._is_heading(blocks[i])), "") if at is not None else ""
for db in ("procedureassist", "procedureassist_staging"):
    eng = create_engine(DATABASE_URL.rsplit("/", 1)[0] + "/" + db)
    with eng.connect() as c:
        pages = c.execute(text("select id, source_text from procedures")).all()
        chunks = c.execute(text("select procedure_id, chunk_index, content from procedure_chunks order by procedure_id, chunk_index")).all()
    stored = {}
    for pid, i, content in chunks: stored.setdefault(pid, []).append(content)
    same = all(rag.chunk_text(t) == stored[p] for p, t in pages)
    diffs = [(pid, b[:60], rag._section_heading(content, b)[:75]) for pid, i, content in chunks for b in content.split("\n\n")
             if old(content, b) != rag._section_heading(content, b)]
    print(f"{db}: stored chunks == chunk_text(source_text) for all {len(pages)} pages: {same}; blocks whose heading changes: {len(diffs)}")
    for d in diffs: print("   ", d)
