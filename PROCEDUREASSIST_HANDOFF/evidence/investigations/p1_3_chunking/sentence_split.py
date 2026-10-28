"""Read-only, in memory: what a sentence-aware cut of over-long paragraphs would change. Today rag.chunk_text cuts a
paragraph longer than CHUNK_SIZE at the last space before the limit; the variant cuts after the last sentence end
(". ") in the second half of the limit, else at a space as today. Prints, per database, every page whose chunks would
change and whether each cut sentence becomes quotable from one chunk. Nothing is embedded or written."""
import re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
import psycopg2
from backend import rag

def chunk_text_sentences(text):
    real = rag.CHUNK_SIZE
    blocks = []
    for block in text.split("\n\n"):
        block = block.strip()
        while len(block) > real:
            end = block.rfind(". ", real // 2, real)
            cut = end + 1 if end > 0 else block.rfind(" ", 0, real)
            cut = cut if cut > 0 else real
            blocks.append(block[:cut].strip())
            block = block[cut:].strip()
        if block:
            blocks.append(block)
    original = rag.chunk_text
    # Reuse chunk_text's grouping by feeding it the pre-cut blocks (each now <= CHUNK_SIZE).
    return original("\n\n".join(blocks))

for db in ("procedureassist", "procedureassist_staging"):
    cur = psycopg2.connect(dbname=db).cursor()
    cur.execute("select id, name, source_text from procedures order by id")
    print("==", db)
    for pid, name, text in cur.fetchall():
        old, new = rag.chunk_text(text), chunk_text_sentences(text)
        if old == new:
            continue
        print(f"  page {pid} {name[:40]}: chunks {len(old)} -> {len(new)}")
        for b in text.split("\n\n"):
            if len(b) > rag.CHUNK_SIZE:
                cut = b.rfind(" ", 0, rag.CHUNK_SIZE)
                start = b.rfind(". ", 0, cut) + 2
                stop = b.find(". ", cut)
                sentence = b[start:stop + 1 if stop > 0 else len(b)]
                whole = lambda chunks: any(rag._words(sentence) in rag._words(c) for c in chunks)
                print(f"    sentence cut today, quotable whole: today {whole(old)}, variant {whole(new)} | {sentence[:110]!r}")
