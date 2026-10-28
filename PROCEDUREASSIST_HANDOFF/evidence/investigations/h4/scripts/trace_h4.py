"""Read-only stage-by-stage trace of one citizen question (H4). DATABASE_URL picks the DB.
Usage: trace_h4.py "<question>" [runs]. Writes nothing to any database."""
import json, os, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app
from backend import rag
from backend.config import IDENTIFY_MIN_SCORE, IDENTIFY_MARGIN
from backend.database import SessionLocal
from backend.models import Procedure
from backend.procedure_search import rank_procedures

Q, RUNS = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1
client = TestClient(app)
print("DB:", os.environ.get("DATABASE_URL", "procedureassist (.env)").rsplit("/", 1)[-1])
print("QUESTION:", Q)

def checks(claim, passages):
    """Each verify_claims condition separately (copied logic, read-only)."""
    text, quote, cid = claim.get("text"), claim.get("quote"), claim.get("chunk_id")
    passage = passages.get(cid) if isinstance(cid, int) else None
    if passage is None or not isinstance(text, str) or not isinstance(quote, str):
        return {"cited chunk retrieved": False}
    W, N = rag._words, rag._normalize
    row = next((b for b in passage.split("\n\n") if W(quote) in W(b)), quote)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", row)
    around = [s for s in sentences if W(quote) in W(s) or W(s) in W(quote)]
    money = rag._money(N(quote)).union(*(rag._money(N(s)) for s in around))
    qn = N(quote)
    return {
        "cited chunk retrieved": True,
        "quote word-for-word in passage": W(quote) in W(passage),
        "quote long enough (>=4 words or whole item)": len(qn.split()) >= rag.MIN_QUOTE_WORDS or rag._whole_item(quote, passage),
        f"numbers in claim {sorted(map(str, rag._numbers(text)))} all in quote {sorted(map(str, rag._numbers(qn) | money))}": rag._numbers(text) <= rag._numbers(qn) | money,
        "all quoted money kept": money <= rag._numbers(text) | rag._money(N(text)),
        "negation agrees": bool(rag.NEGATION.search(N(text))) == bool(rag.NEGATION.search(qn)),
        "no back-reference opening": not rag.BACK_REFERENCE.match(qn),
        f"document kinds {sorted(rag._document_kinds(text))} in heading/quote": rag._document_kinds(text) <= set(W(f"{rag._section_heading(passage, quote)} {quote}").split()),
    }

# 1-2. Normalisation and identification through the real endpoint.
ident = client.post("/api/identify", json={"question": Q, "language": "en"}).json()
print("\n[1-2] /api/identify ->", json.dumps({k: v for k, v in ident.items() if k != "candidates"}, ensure_ascii=False),
      [(c["id"], c["name"]) for c in ident.get("candidates", [])])
with SessionLocal() as db:
    vector = rag.embed_texts([Q], query=True)[0]
    print(f"     ranking (min {IDENTIFY_MIN_SCORE}, margin {IDENTIFY_MARGIN}):",
          [(pid, db.get(Procedure, pid).name, round(s, 4)) for pid, s in rank_procedures(db, vector)[:5]])
    if ident.get("status") != "matched":
        sys.exit("not matched; stop")
    proc = db.get(Procedure, ident["candidates"][0]["id"])
    # 3-5. Retrieval and context.
    chunks = rag.retrieve(db, proc.id, Q)
    sims = {c.id: 1 - rag.ProcedureChunk.embedding.comparator for c in []}
    print(f"\n[3-5] retrieve(procedure {proc.id} '{proc.name}', limit {rag.GUIDANCE_PASSAGES}) -> chunks", [c.id for c in chunks],
          f"(page has {len(proc.chunks) if hasattr(proc, 'chunks') else '?'} chunks)")
    for c in chunks:
        print(f"     chunk {c.id} (index {c.chunk_index}, {len(c.content)} chars): {c.content!r}")
    prompt = rag.build_guidance_prompt(Q, chunks)
    print(f"     prompt length {len(prompt)} chars; no truncation in code (num_ctx from config)")
    passages = {c.id: c.content for c in chunks}
    for run in range(1, RUNS + 1):
        # 6. Model output, raw.
        raw = rag._ask(prompt)
        print(f"\n[6] run {run} raw model JSON: {json.dumps(raw, ensure_ascii=False)}")
        # 7-8. Citations and each verification condition.
        for cl in raw.get("claims", []) if isinstance(raw, dict) else []:
            print(f"  [7-8] claim: {cl.get('text')!r}\n        quote: {cl.get('quote')!r} chunk {cl.get('chunk_id')}")
            for name, ok in checks(cl, passages).items():
                print(f"        {'PASS' if ok else 'FAIL'}  {name}")
        kept = rag.verify_claims(raw.get("claims", []), passages) if isinstance(raw, dict) else []
        print(f"  verify_claims kept {len(kept)}")
        if kept:
            checked, complete = rag.check_claims(Q, kept, chunks)
            print(f"  check_claims kept {len(checked)} complete={complete}")
# 9. Final answer through the real endpoint.
final = client.post("/api/guidance", json={"procedure_id": ident["candidates"][0]["id"], "question": Q, "language": "en"}).json()
print("\n[9] /api/guidance ->", json.dumps(final, ensure_ascii=False))
