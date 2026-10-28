"""Read-only W11 evaluation (embeddings only; no generation; nothing written). DATABASE_URL picks the database.
Every labelled English question from the existing fixtures and the Stage 1 audit probe, with its source:
  expected page(s), the expected page's rank and score among ALL pages, the top two pages and scores, and the decision
  procedure_search._decide makes today on the whole message (need extraction is not replayed).
Then: a threshold sweep (classify's min_score varied; everything else as implemented) and a top-two margin analysis."""
import json, os, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from sqlalchemy import func
from backend import rag, procedure_search as ps
from backend.config import IDENTIFY_MARGIN, IDENTIFY_MIN_SCORE
from backend.database import SessionLocal
from backend.models import Procedure, ProcedureChunk

ROOT = "/Users/arunnm/Projects/SOP/"
DB = os.environ.get("DATABASE_URL", "procedureassist").rsplit("/", 1)[-1]

def load_cases(pages):
    by_frag = lambda frag: [p.id for p in pages if frag in p.source_url]
    cases = []  # (source, question, kind, expected ids)  kind: page | none | ambiguous
    for f in ("answers", "heldout"):
        for i, c in enumerate(json.load(open(ROOT + f"fixtures/evaluation/{f}.json"))["cases"]):
            if c.get("language") == "ta" or "context" in c or c.get("clarification") or len(c["expected"]) != 1:
                continue
            e = c["expected"][0]
            kind = "none" if e is None else "ambiguous" if e == "ambiguous" else "page"
            cases.append((f"{f}[{i}]", c["message"], kind, by_frag(e) if kind == "page" else []))
    for f in ("population", "demo_services"):
        for i, c in enumerate(json.load(open(ROOT + f"fixtures/evaluation/{f}.json"))["cases"]):
            e = c.get("expected") or [None]
            if len(e) > 1 or c.get("relation"):
                continue
            kind = "none" if e[0] is None else "ambiguous" if e[0] == "ambiguous" else "page"
            cases.append((f"{f}[{i}]", c["message"], kind, by_frag(e[0]) if kind == "page" else []))
    ident = json.load(open(ROOT + "fixtures/evaluation/identification.json"))
    for i, q in enumerate(ident["questions"]):
        urls = [ident["procedures"][n] for n in q["expected"]]
        ids = [p.id for p in pages if p.source_url in urls]
        if q["expected"] and len(ids) == len(urls) == 1:
            cases.append((f"identification[{i}]", q["question"], "page", ids))
        elif not q["expected"]:
            cases.append((f"identification[{i}]", q["question"], "none", []))
    for l in open(ROOT + "PROCEDUREASSIST_HANDOFF/evidence/investigations/rag_audit/probe_staging.jsonl"):
        r = json.loads(l)
        if r["group"] != "F":  # follow-ups are routed differently
            ids = [i for i in r["expected"] if any(p.id == i for p in pages)]
            if ids:
                cases.append(("audit_probe", r["q"], "page", ids))
    return [c for c in cases if c[2] != "page" or c[3]]

def all_scores(db, vector):
    score = func.max(1 - ProcedureChunk.embedding.cosine_distance(vector)).label("s")
    return [(r.procedure_id, float(r.s)) for r in db.query(ProcedureChunk.procedure_id, score).group_by(ProcedureChunk.procedure_id).order_by(score.desc())]

def decide(db, vector, text, min_score):
    """procedure_search._decide with classify's min_score as a parameter (nothing else changed)."""
    ranked = ps.rank_procedures(db, vector)
    status, ids = ps.classify(ranked, min_score=min_score)
    if acronyms := ps.ACRONYM.findall(text):
        near = [i for i, s in ranked if s >= ps.ACRONYM_MIN_SCORE]
        nearby = db.query(Procedure).filter(Procedure.id.in_(near)).all()
        named = [p.id for p in nearby if any(ps.abbreviates(a, p.name) for a in acronyms)]
        if not named and status != "matched":
            uses = lambda p: any(re.search(rf"\b{re.escape(a)}\b", p.source_text) for a in acronyms)
            named = [p.id for p in db.query(Procedure) if uses(p)]
            named = named if len(named) == 1 and named[0] in near else []
        if len(named) == 1:
            status, ids = "matched", named
    found = {p.id: p for p in db.query(Procedure).filter(Procedure.id.in_(ids))}
    procedures = [found[i] for i in ids if ps.mentions(found[i].source_text, text)]
    if not procedures:
        return "no_match", []
    if status == "ambiguous" and len(procedures) == 1:
        return "ambiguous", ids
    if len(procedures) > 1 and (page := ps.named_by_the_others(text, procedures)):
        return "matched", [page.id]
    return ("matched" if len(procedures) == 1 else "ambiguous"), [p.id for p in procedures]

def verdict(kind, expected, status, ids):
    if kind == "none":
        return "correct" if status == "no_match" else "FALSE MATCH" if status == "matched" else "ambiguous (safe)"
    if kind == "ambiguous":
        return "correct" if status != "matched" else "FORCED MATCH"
    if status == "matched":
        return "correct" if ids[0] in expected else "WRONG PAGE"
    if status == "ambiguous":
        return "asks (expected among)" if any(i in expected for i in ids) else "asks (expected absent)"
    return "MISSED (no_match)"

def main():
  with SessionLocal() as db:
      pages = db.query(Procedure).all()
      name = {p.id: p.name[:32] for p in pages}
      cases = load_cases(pages)
      vectors = rag.embed_texts([c[1] for c in cases], query=True)
      rows = []
      for (src, q, kind, expected), v in zip(cases, vectors):
          scores = all_scores(db, v)
          rank = next((n for n, (pid, _) in enumerate(scores, 1) if pid in expected), None)
          exp_score = next((s for pid, s in scores if pid in expected), None)
          status, ids = decide(db, v, q, IDENTIFY_MIN_SCORE)
          rows.append(dict(src=src, q=q, kind=kind, expected=expected, rank=rank, exp_score=exp_score, top=scores[0], second=scores[1],
                           status=status, ids=ids, verdict=verdict(kind, expected, status, ids), vector=v))
      print(f"### database {DB}: {len(rows)} labelled questions ({sum(r['kind']=='page' for r in rows)} in scope, "
            f"{sum(r['kind']=='none' for r in rows)} out of scope, {sum(r['kind']=='ambiguous' for r in rows)} ambiguous)")
      print("\n## every question (today's decision)")
      for r in rows:
          exp = f"{r['expected']} rank {r['rank']} {r['exp_score']:.3f}" if r["kind"] == "page" else r["kind"]
          print(f"  {r['verdict']:22} {r['src']:18} top {name[r['top'][0]]}:{r['top'][1]:.3f} 2nd {name[r['second'][0]]}:{r['second'][1]:.3f} "
                f"| {r['status']} {r['ids']} | expected {exp} | {r['q'][:70]}")
      from collections import Counter
      print("\n## today's outcome counts:", dict(Counter(r["verdict"] for r in rows)))
      inscope = [r for r in rows if r["kind"] == "page"]
      print("## in-scope: expected page rank 1:", sum(r["rank"] == 1 for r in inscope), "| rank 2-3:", sum(r["rank"] in (2, 3) for r in inscope),
            "| rank >3 (outside the candidate set):", sum(r["rank"] > 3 for r in inscope), "of", len(inscope))
      print("## in-scope expected-page scores below 0.53:")
      for r in sorted(inscope, key=lambda r: r["exp_score"]):
          if r["exp_score"] < IDENTIFY_MIN_SCORE:
              print(f"    {r['exp_score']:.3f} rank {r['rank']} {r['verdict']:20} {r['src']:18} {r['q'][:70]}")
      print("## out-of-scope top scores (highest first):")
      for r in sorted([r for r in rows if r["kind"] == "none"], key=lambda r: -r["top"][1])[:12]:
          print(f"    {r['top'][1]:.3f} {name[r['top'][0]]:32} {r['verdict']:18} {r['src']:18} {r['q'][:60]}")
      print("\n## threshold sweep (classify min_score; everything else as implemented)")
      print("   t     in-scope correct  wrong page  missed  asks   | out-of-scope false match  asks | ambiguous forced")
      for t in [x / 100 for x in range(45, 61)]:
          c = Counter()
          for r in rows:
              st, ids = decide(db, r["vector"], r["q"], t)
              c[(r["kind"], verdict(r["kind"], r["expected"], st, ids).split(" (")[0])] += 1
          print(f"  {t:.2f}{'*' if abs(t-IDENTIFY_MIN_SCORE)<1e-9 else ' '}  {c[('page','correct')]:8} {c[('page','WRONG PAGE')]:11} {c[('page','MISSED')]:7} "
                f"{c[('page','asks')]:6}  | {c[('none','FALSE MATCH')]:14} {c[('none','ambiguous')]:12} | {c[('ambiguous','FORCED MATCH')]:6}")
      print("\n## top-two margin (in-scope, top score >= 0.45): is the top page right?")
      for lo, hi in [(0, 0.01), (0.01, 0.02), (0.02, 0.03), (0.03, 0.05), (0.05, 0.08), (0.08, 0.12), (0.12, 1)]:
          band = [r for r in inscope if r["top"][1] >= 0.45 and lo <= r["top"][1] - r["second"][1] < hi]
          right = sum(r["top"][0] in r["expected"] for r in band)
          print(f"    gap {lo:.2f}-{hi:.2f}: {len(band):3} questions, top page right {right}, wrong {len(band) - right}")
      print("## out-of-scope margin vs top score:")
      for r in sorted([r for r in rows if r["kind"] == "none"], key=lambda r: -r["top"][1])[:8]:
          print(f"    top {r['top'][1]:.3f} gap {r['top'][1]-r['second'][1]:.3f}  {r['q'][:60]}")


if __name__ == "__main__":
    main()
