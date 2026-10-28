"""Read-only: raw model claims for one question and which verify_claims check rejects each."""
import sys, os
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure
Q = sys.argv[1]
print("DB:", os.environ.get("DATABASE_URL", "approved(.env)").rsplit("/", 1)[-1])
with SessionLocal() as db:
    pid = db.query(Procedure).filter(Procedure.source_url.like(sys.argv[2])).one().id
    chunks = rag.retrieve(db, pid, Q)
    print("retrieved", [c.id for c in chunks])
    raw = rag._ask(rag.build_guidance_prompt(Q, chunks))
    passages = {c.id: c.content for c in chunks}
    for cl in raw.get("claims", []):
        p = passages.get(cl.get("chunk_id"), "")
        print("\nCLAIM:", cl.get("text")); print("QUOTE:", cl.get("quote"), "| chunk", cl.get("chunk_id"))
        print("  kinds(text):", rag._document_kinds(cl["text"]), " heading:", repr(rag._section_heading(p, cl["quote"])))
        print("  verified:", bool(rag.verify_claims([cl], passages)))
    print("insufficient:", raw.get("insufficient_evidence"))
