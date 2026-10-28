"""Read-only (embeddings only): two W11 options.
C: page scores when DL/RC in an English query are written in full (the Tamil normaliser already does this).
E: which distinct labelled questions fall in the band ACRONYM_MIN_SCORE (0.45) <= best < IDENTIFY_MIN_SCORE (0.53),
   where the system could offer its best page as a choice ("Did you mean ...?") instead of no match."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag, procedure_search as ps
from backend.config import IDENTIFY_MIN_SCORE
from backend.database import SessionLocal
from backend.models import Procedure
from w11_eval import load_cases, all_scores, decide, verdict
EXPAND = {r"\bRCs?\b": "registration certificate (RC)", r"\bDLs?\b": "driving licence (DL)"}
with SessionLocal() as db:
    pages = db.query(Procedure).all(); name = {p.id: p.name[:30] for p in pages}
    print("== C: DL/RC written in full")
    for q in ["How much do I pay to get my DL renewed?", "How much does a duplicate RC cost?", "sold my bike, need to transfer the RC",
              "Can I renew my DL early?", "What is the fee to renew the RC of a motorcycle?", "How do I renew my RC?",
              "I lost my DL, what should I do?", "What documents are needed to renew my vehicle RC?"]:
        full = q
        for pat, words in EXPAND.items():
            full = re.sub(pat, words, full)
        for label, text in (("as asked", q), ("spelled out", full)):
            v = rag.embed_texts([text], query=True)[0]
            r = ps.rank_procedures(db, v); st, ids = decide(db, v, text, IDENTIFY_MIN_SCORE)
            print(f"  {label:11} {[(name[i], round(s, 3)) for i, s in r[:2]]} -> {st} {[name[i] for i in ids]} | {text[:75]}")
    print("\n== E: distinct questions in the band 0.45 <= best < 0.53 (today: no match unless an abbreviation decides)")
    seen, rows = set(), []
    for c in load_cases(pages):
        if c[1].lower() not in seen:
            seen.add(c[1].lower()); rows.append(c)
    vectors = rag.embed_texts([c[1] for c in rows], query=True)
    for (src, q, kind, expected), v in zip(rows, vectors):
        s = all_scores(db, v); best = s[0]
        if ps.ACRONYM_MIN_SCORE <= best[1] < IDENTIFY_MIN_SCORE:
            st, ids = decide(db, v, q, IDENTIFY_MIN_SCORE)
            offered_right = kind == "page" and best[0] in expected
            print(f"  {kind:9} best {name[best[0]]}:{best[1]:.3f} offered page {'RIGHT' if offered_right else 'wrong' if kind == 'page' else '(none exists)'} "
                  f"| today {st} | {src:18} {q[:65]}")
