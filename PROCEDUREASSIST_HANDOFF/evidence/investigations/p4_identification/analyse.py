"""Summarise validator_experiment.py output: what each policy would decide, per question and in total (read-only)."""
import json, sys
from collections import Counter

def verdict(kind, expected, status, ids):
    if kind == "none":
        return "correct" if status == "no_match" else "FALSE MATCH" if status == "matched" else "asks (safe)"
    if kind == "ambiguous":
        return "correct" if status != "matched" else "FORCED MATCH"
    if status == "matched":
        return "correct" if ids[0] in expected else "WRONG PAGE"
    if status == "ambiguous":
        return "asks"
    return "MISSED"

def policy(r, variant, recover):
    status, ids, checks = r["status"], list(r["ids"]), {int(k): v[variant] for k, v in r["checks"].items()}
    if status == "matched" and checks.get(ids[0]) == "no":
        return "no_match", []
    if status == "ambiguous":
        kept = [i for i in ids if checks.get(i) != "no"]
        return ("no_match", []) if not kept else ("ambiguous", kept)
    if status == "no_match" and recover and checks:
        top = int(next(iter(checks)))
        if checks[top] == "yes":
            return "matched", [top]
    return status, ids

rows = [json.loads(l) for path in sys.argv[1:] for l in open(path)]
answers = Counter(a for r in rows for c in r["checks"].values() for a in c.values())
print(f"{len(rows)} questions; validator answers: {dict(answers)}")
policies = {"today": None, "veto A": ("A", False), "veto B": ("B", False), "veto A + recover": ("A", True), "veto B + recover": ("B", True)}
totals = {}
for name, p in policies.items():
    c = Counter()
    for r in rows:
        st, ids = (r["status"], r["ids"]) if p is None else policy(r, *p)
        v = verdict(r["kind"], r["expected"], st, ids)
        c[(r["kind"], v)] += 1
        r.setdefault("v", {})[name] = v
    totals[name] = c
print("\npolicy            | in scope: correct  wrong  missed  asks | out of scope: false match  correct | ambiguous forced")
for name, c in totals.items():
    print(f"{name:17} | {c[('page','correct')]:17} {c[('page','WRONG PAGE')]:6} {c[('page','MISSED')]:7} {c[('page','asks')]:5} |"
          f" {c[('none','FALSE MATCH')]:24} {c[('none','correct')]:8} | {c[('ambiguous','FORCED MATCH')]:5}")
print("\nquestions whose outcome changes under any policy:")
for r in rows:
    if len(set(r["v"].values())) > 1:
        checks = {k: f"{v['A']}/{v['B']}" for k, v in r["checks"].items()}
        print(f"  {r['kind']:5} {r['src'][:18]:18} today {r['v']['today']:12} vetoA {r['v']['veto A']:12} vetoB {r['v']['veto B']:12} "
              f"+recA {r['v']['veto A + recover']:12} +recB {r['v']['veto B + recover']:12} checks(A/B) {checks} | {r['q'][:70]}")
