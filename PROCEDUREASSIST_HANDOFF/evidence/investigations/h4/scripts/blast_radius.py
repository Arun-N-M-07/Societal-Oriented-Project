"""Read-only H4 blast-radius probe. Runs scripts/evaluate_answers.py unchanged, but wraps
rag.verify_claims in memory to log every claim it rejects: which checks fail, and whether
the quote would match the passage if only a/an/the were treated as interchangeable
(substitution only: the same number of words). Writes one JSON line per rejected claim to
the file named by H4_LOG. Changes no code, data or fixtures; scores printed are NOT results."""
import json, os, re, runpy, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
import backend.rag as rag

LOG = open(os.environ["H4_LOG"], "a")
ARTICLE = re.compile(r" (?:a|an|the)(?= )")
original = rag.verify_claims

def conditions(claim, passages):
    text, quote, cid = claim.get("text"), claim.get("quote"), claim.get("chunk_id")
    passage = passages.get(cid) if isinstance(cid, int) else None
    if passage is None or not isinstance(text, str) or not isinstance(quote, str):
        return {"cited_chunk": False}, None
    W, N = rag._words, rag._normalize
    row = next((b for b in passage.split("\n\n") if W(quote) in W(b)), quote)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", row)
    around = [s for s in sentences if W(quote) in W(s) or W(s) in W(quote)]
    money = rag._money(N(quote)).union(*(rag._money(N(s)) for s in around))
    qn = N(quote)
    art = ARTICLE.sub(" _", W(quote)) in ARTICLE.sub(" _", W(passage))
    return {
        "verbatim": W(quote) in W(passage),
        "length": len(qn.split()) >= rag.MIN_QUOTE_WORDS or rag._whole_item(quote, passage),
        "numbers": rag._numbers(text) <= rag._numbers(qn) | money,
        "money_kept": money <= rag._numbers(text) | rag._money(N(text)),
        "negation": bool(rag.NEGATION.search(N(text))) == bool(rag.NEGATION.search(qn)),
        "back_reference": not rag.BACK_REFERENCE.match(qn),
        "document_kind": rag._document_kinds(text) <= set(W(f"{rag._section_heading(passage, quote)} {quote}").split()),
    }, art

def logged(claims, passages):
    kept = original(claims, passages)
    kept_texts = {k["text"] for k in kept}
    for claim in claims if isinstance(claims, list) else []:
        if not isinstance(claim, dict) or str(claim.get("text", "")).strip() in kept_texts:
            continue
        conds, art = conditions(claim, passages)
        LOG.write(json.dumps({"claim": claim, "failed": [k for k, v in conds.items() if not v],
                              "article_match": art}, ensure_ascii=False) + "\n")
    LOG.flush()
    return kept

rag.verify_claims = logged
sys.argv = ["evaluate_answers.py"] + sys.argv[1:]
runpy.run_path("/Users/arunnm/Projects/SOP/scripts/evaluate_answers.py", run_name="__main__")
