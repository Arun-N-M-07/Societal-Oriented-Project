"""Run scripts/evaluate_answers.py with the current verify_claims ("new") or the pre-session one ("old"). Read-only."""
import runpy, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
import backend.rag as rag
import re
from backend.rag import _normalize, _numbers, _words, _whole_item, MIN_QUOTE_WORDS, NEGATION, NUMBER_WORDS, SCALES

# The pre-session money parser: "Rs./Rupees" before the amount only, "hundred" alone = 0.
OLD_MONEY = re.compile(r"(?:rs\.?|₹|inr|rupees)\s*(\d[\d,]*(?:\.\d+)?|(?:(?:[a-z]+(?:ty|teen)|one|two|three|four|five|six|seven"
                       r"|eight|nine|ten|eleven|twelve|hundred|thousand|lakh|crore|and)\s*)+)")

def _old_amount(text):
    if text[0].isdigit():
        return float(text.replace(",", ""))
    total = current = 0
    for word in text.split():
        if word in NUMBER_WORDS: current += NUMBER_WORDS[word]
        elif word == "hundred": current *= 100
        elif word in SCALES: total, current = total + current * SCALES[word], 0
    return float(total + current)

def _money(text):
    return {_old_amount(m.strip()) for m in OLD_MONEY.findall(text)}

def old_verify_claims(claims, passages):
    verified = []
    for claim in claims if isinstance(claims, list) else []:
        if not isinstance(claim, dict):
            continue
        text, quote, chunk_id = claim.get("text"), claim.get("quote"), claim.get("chunk_id")
        if not (isinstance(text, str) and text.strip() and isinstance(quote, str)):
            continue
        passage = passages.get(chunk_id) if isinstance(chunk_id, int) else None
        quote_n = _normalize(quote)
        money = _money(quote_n)
        if not money <= _numbers(text) and _words(text) in _words(quote):
            text = quote
        if (
            passage is None
            or len(quote_n.split()) < MIN_QUOTE_WORDS and not _whole_item(quote, passage)
            or _words(quote) not in _words(passage)
            or not _numbers(text) <= _numbers(quote_n) | money
            or not money <= _numbers(text) | _money(_normalize(text))
            or bool(NEGATION.search(_normalize(text))) != bool(NEGATION.search(quote_n))
        ) or any(v["text"] == text.strip() for v in verified):
            continue
        verified.append({"text": text.strip(), "chunk_id": chunk_id, "quote": quote.strip()})
    return verified

if sys.argv[1] == "old":
    rag.verify_claims = old_verify_claims
sys.argv = ["evaluate_answers.py"] + sys.argv[2:]
runpy.run_path("/Users/arunnm/Projects/SOP/scripts/evaluate_answers.py", run_name="__main__")
