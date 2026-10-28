"""Read-only: RC answers with their quotes (top5 and continuation), and whether a document-kind guard that reads
"RC" as "registration certificate" (and "DL" as "driving licence") would keep each claim. Nothing is changed."""
import re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
sys.path.insert(0, "/private/tmp/claude-501/-Users-arunnm-Projects-SOP/bebaf14e-7bdf-4da2-8b3f-9c2a6edb540d/scratchpad/h3")
from backend import rag
from backend.database import SessionLocal
from variants import continuation
EXPAND = {r"\bRCs?\b": "registration certificate", r"\bDLs?\b": "driving licence"}
def guarded_kinds(text):
    for pat, words in EXPAND.items():
        text = re.sub(pat, words, text)
    return rag._document_kinds(text)
with SessionLocal() as db:
    for q in ["What is the fee to renew my vehicle RC?", "What is the fee to renew the RC of a motorcycle?",
              "What is the fee to renew the registration certificate of my motorcycle?", "RC renewal fee for a car", "How much does a duplicate RC cost?"]:
        base = rag.retrieve(db, 39, q)
        for name, chunks in (("top5", base), ("continue", continuation(db, base))):
            passages = {c.id: c.content for c in chunks}
            claims, _ = rag._answer(q, chunks)
            kept, _ = rag.check_claims(q, claims, chunks) if claims else ([], False)
            print(f"\n## {q} [{name}]")
            for c in kept:
                heading = rag._section_heading(passages[c["chunk_id"]], c["quote"])
                ok = guarded_kinds(c["text"]) <= set(rag._words(f"{heading} {c['quote']}").split())
                print(f"  {'KEEP  ' if ok else 'REJECT'} kinds={sorted(guarded_kinds(c['text']))}\n     claim: {c['text'][:140]}\n     quote: {c['quote'][:140]}")
