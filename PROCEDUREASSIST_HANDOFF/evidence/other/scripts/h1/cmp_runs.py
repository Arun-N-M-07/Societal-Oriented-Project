"""Compare two evaluate_answers outputs per question: pass/fail, claims count, partial flag."""
import re, sys
def load(path):
    out = {}
    for line in open(path):
        m = re.match(r"^(ok|FAIL)\s+\[([^\]]+)\]\s(.{60})\s*(.*)$", line.rstrip("\n"))
        if m:
            st, cat, q, rest = m.groups()
            out[(cat, q.strip())] = (st, re.sub(r"\s*\(\d+s\)$", "", rest).strip())
    return out
a, b = load(sys.argv[1]), load(sys.argv[2])
print(f"{len(a)} vs {len(b)} questions")
for k in a:
    if a[k] != b.get(k):
        print(f"[{k[0]}] {k[1]}\n    before: {a[k]}\n    after:  {b.get(k)}")
