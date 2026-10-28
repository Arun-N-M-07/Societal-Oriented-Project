"""Read-only: replay candidate claim rules on claims the current code verified. Input: evaluate_answers.py --claims
outputs (one JSON line per final claim). DATABASE_URL picks the database whose chunks the claims cite. Nothing is written.
For each rule, prints every currently verified claim it would reject, so false rejections can be judged by hand.
  R1  a quote cut from an answer opening with "Yes"/"No" includes that word;
  R1b a bare "Yes"/"No" quote sits directly under its question;
  R2  every period (number + year/month/week/day) of the quoted sentence or row is in the claim, with its unit;
  R2q every period of the quote itself is in the claim, with its unit;
  RU  every period in the claim is one the quote (or its sentence) states, with the same unit;
  R3  an amount claimed for a test, duplicate or renewal comes from a row (or the heading directly above it) saying so.
      Not _section_heading: it returns the nearest heading above, which for page 39 row 11 (certificate of fitness) is
      item 10's "Conducting test of a vehicle ...:" header."""
import json, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend.database import SessionLocal
from backend.models import ProcedureChunk
from backend import rag
from backend.rag import _amount, _IN_WORDS, _money, _normalize, _section_heading, _words

DURATION = re.compile(rf"\b(\d+|{_IN_WORDS})[\s-]*(year|month|week|day)s?\b")
YES_NO = re.compile(r"(?:yes|no)\b")
SERVICES = ("test", "duplicate", "renew")

def durations(text):
    return {(v, unit) for n, unit in DURATION.findall(text.lower().replace("-", " ")) if (v := _amount(n.strip()))}

def services(text):
    return {s for s in SERVICES if re.search(rf"\b{s}", _normalize(text))}

def context(claim, passage):
    quote = claim["quote"]
    blocks = passage.split("\n\n")
    at = next((i for i, b in enumerate(blocks) if _words(quote) in _words(b)), None)
    row = blocks[at] if at is not None else quote
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", row)
    around = [s for s in sentences if _words(quote) in _words(s) or _words(s) in _words(quote)]
    return blocks, at, row, around, _section_heading(passage, quote)

def rules(claim, passage):
    text, quote = claim["text"], claim["quote"]
    blocks, at, row, around, heading = context(claim, passage)
    periods = durations(quote).union(*map(durations, around))
    bad = []
    if YES_NO.match(_normalize(row)) and not YES_NO.match(_normalize(quote)):
        bad.append("R1")
    if _normalize(quote).strip(" .") in ("yes", "no") and not (at and blocks[at - 1].endswith("?")):
        bad.append("R1b")
    if not periods <= durations(text):
        bad.append("R2")
    if not durations(quote) <= durations(text):
        bad.append("R2q")
    if not durations(text) <= periods:
        bad.append("RU")
    lead = blocks[at - 1] if at and rag._is_heading(blocks[at - 1]) else ""
    if _money(_normalize(text)) and not services(text) <= services(f"{lead} {row}"):
        bad.append("R3")
    return bad

claims = []
for path in sys.argv[1:]:
    for line in open(path):
        if line.strip().startswith("claim {"):
            claims.append((path.rsplit("/", 1)[-1], json.loads(line.strip()[6:])))
with SessionLocal() as db:
    content = dict(db.query(ProcedureChunk.id, ProcedureChunk.content))
    counts, seen = {}, set()
    for src, claim in claims:
        key = (claim["chunk_id"], claim["text"], claim["quote"])
        if key in seen:
            continue
        seen.add(key)
        passage = content.get(claim["chunk_id"])
        if passage is None:
            print("MISSING CHUNK", src, claim); continue
        still = rag.verify_claims([claim], {claim["chunk_id"]: passage})
        for r in rules(claim, passage):
            counts[r] = counts.get(r, 0) + 1
            print(f"{r:4} {src:28} [{claim['procedure_id']}/{claim['chunk_id']}] {claim['text'][:120]!r} <- {claim['quote'][:120]!r}"
                  f"{'' if still else '  (current verify_claims also rejects it)'}")
    print(f"\n{len(seen)} distinct verified claims replayed; would reject: {counts}")
