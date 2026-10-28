"""Read-only W11 analysis on top of w11_eval.py (embeddings only, except the last step which calls the real /api/identify):
  1. questions de-duplicated by text (the fixture sets repeat some);
  2. the cause of every miss: threshold (best score < 0.53), name check (procedure_search.mentions), or other;
  3. a de-duplicated threshold sweep;
  4. a margin variant: a second candidate within IDENTIFY_MARGIN of the best makes the call ambiguous even if it scores
     below the threshold (today it must also clear the threshold);
  5. the real /api/identify outcome (need extraction included) for every question that is not correct today."""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend import rag, procedure_search as ps
from backend.config import IDENTIFY_MARGIN, IDENTIFY_MIN_SCORE
from backend.database import SessionLocal
from backend.main import app
from backend.models import Procedure
from w11_eval import load_cases, all_scores, decide, verdict

DB = os.environ.get("DATABASE_URL", "procedureassist").rsplit("/", 1)[-1]

def decide_margin(db, vector, text):
    """decide() with classify's margin applied to every top-3 candidate once the best clears the threshold."""
    real = ps.classify
    def classify(ranked, min_score=IDENTIFY_MIN_SCORE, margin=IDENTIFY_MARGIN):
        if not ranked or ranked[0][1] < min_score:
            return "no_match", []
        close = [pid for pid, s in ranked[:ps.MAX_CANDIDATES] if ranked[0][1] - s <= margin]
        return ("matched" if len(close) == 1 else "ambiguous"), close
    ps.classify = classify
    try:
        return decide(db, vector, text, IDENTIFY_MIN_SCORE)
    finally:
        ps.classify = real

with SessionLocal() as db:
    pages = db.query(Procedure).all()
    name = {p.id: p.name[:30] for p in pages}
    seen, cases = set(), []
    for c in load_cases(pages):
        if c[1].lower() not in seen:
            seen.add(c[1].lower()); cases.append(c)
    vectors = rag.embed_texts([c[1] for c in cases], query=True)
    rows = []
    for (src, q, kind, expected), v in zip(cases, vectors):
        scores = all_scores(db, v)
        st, ids = decide(db, v, q, IDENTIFY_MIN_SCORE)
        ranked = ps.rank_procedures(db, v)
        cst, cids = ps.classify(ranked)
        cause = ""
        if kind == "page" and st == "no_match":
            cause = "threshold" if scores[0][1] < IDENTIFY_MIN_SCORE else ("name check" if cst != "no_match" else "other")
        rows.append(dict(src=src, q=q, kind=kind, expected=expected, v=v, scores=scores, st=st, ids=ids,
                         verdict=verdict(kind, expected, st, ids), cause=cause))
    print(f"### {DB}: {len(rows)} distinct questions ({sum(r['kind']=='page' for r in rows)} in scope, "
          f"{sum(r['kind']=='none' for r in rows)} out of scope, {sum(r['kind']=='ambiguous' for r in rows)} ambiguous)")
    print("outcomes today:", dict(Counter(r["verdict"] for r in rows)))
    print("\n## misses (in scope, no match) and their cause")
    for r in rows:
        if r["cause"]:
            print(f"  {r['cause']:11} best {name[r['scores'][0][0]]}:{r['scores'][0][1]:.3f} | {r['src']:18} {r['q'][:75]}")
    print("\n## de-duplicated threshold sweep")
    print("   t     correct  wrong  missed  asks | out-of-scope false match | ambiguous forced")
    for t in [x / 100 for x in range(45, 61)]:
        c = Counter((r["kind"], verdict(r["kind"], r["expected"], *decide(db, r["v"], r["q"], t)).split(" (")[0]) for r in rows)
        print(f"  {t:.2f}{'*' if abs(t - IDENTIFY_MIN_SCORE) < 1e-9 else ' '}  {c[('page','correct')]:6} {c[('page','WRONG PAGE')]:6} {c[('page','MISSED')]:7} "
              f"{c[('page','asks')]:5} | {c[('none','FALSE MATCH')]:12} | {c[('ambiguous','FORCED MATCH')]:6}")
    print("\n## margin variant (second candidate below the threshold also counts as close)")
    changes = Counter()
    for r in rows:
        st, ids = decide_margin(db, r["v"], r["q"])
        new = verdict(r["kind"], r["expected"], st, ids)
        if new != r["verdict"]:
            changes[(r["verdict"], new)] += 1
            print(f"  {r['verdict']:22} -> {new:22} | {r['src']:18} {r['q'][:70]}")
    print("  summary:", dict(changes))

print("\n## real /api/identify for every question not correct today (need extraction included)")
client = TestClient(app)
for r in rows:
    if r["verdict"] != "correct":
        body = client.post("/api/identify", json={"question": r["q"], "language": "en"}).json()
        got = [c["id"] for c in body.get("candidates", [])]
        real = verdict(r["kind"], r["expected"], body.get("status"), got) if body.get("status") != "multiple" else "multiple"
        print(f"  whole-message {r['verdict']:22} | real API {body.get('status')} {got} -> {real:22} | {r['q'][:70]}")
