"""Compare two evaluate_answers.py outputs case by case (read-only): prints every case whose pass/fail, stage,
detail or claims changed, then both runs' summary lines. Claims come from --claims runs when present.
    cmp_eval.py <before.txt> <after.txt>"""
import json, re, sys

def load(path):
    cases, summary, last = {}, [], None
    for line in open(path):
        line = line.rstrip("\n")
        m = re.match(r"^(ok  |FAIL|SKIP) \[([^\]]+)\] (.{60}) ?(.*)$", line)
        if m:
            status, cat, q, rest = m.groups()
            key = (cat, q.strip())
            while key in cases:  # the same question asked twice (e.g. routed and in context)
                key = (key[0], key[1] + "'")
            cases[key] = {"status": status.strip(), "rest": re.sub(r"\s*\(\d+s\)$", "", rest).strip(), "claims": []}
            last = key
        elif line.strip().startswith("claim {") and last:
            c = json.loads(line.strip()[6:])
            cases[last]["claims"].append(c["text"])
        elif line and not line.startswith(" ") or line.startswith("  ") and ":" in line and not line.strip().startswith("claim"):
            if not m:
                summary.append(line)
    return cases, summary

(a, sa), (b, sb) = load(sys.argv[1]), load(sys.argv[2])
# Claims are compared only when both runs printed them (--claims).
with_claims = any(c["claims"] for c in a.values()) and any(c["claims"] for c in b.values())
changed = 0
for key in list(a) + [k for k in b if k not in a]:
    x, y = a.get(key), b.get(key)
    if x is None or y is None or (x["status"], x["rest"]) != (y["status"], y["rest"]) or with_claims and x["claims"] != y["claims"]:
        changed += 1
        print(f"[{key[0]}] {key[1]}")
        for label, r in (("before", x), ("after ", y)):
            print(f"   {label}: {'(absent)' if r is None else r['status'] + ' ' + r['rest'][:150]}")
            if r and x and y and with_claims and x["claims"] != y["claims"]:
                for t in r["claims"]:
                    print(f"        - {t[:140]}")
print(f"\n{changed} of {len(set(a) | set(b))} cases changed")
print("before:", *[s for s in sa if re.match(r"^(\d+/\d+|outcomes|failures|identification)", s)], sep="\n  ")
print("after: ", *[s for s in sb if re.match(r"^(\d+/\d+|outcomes|failures|identification)", s)], sep="\n  ")
