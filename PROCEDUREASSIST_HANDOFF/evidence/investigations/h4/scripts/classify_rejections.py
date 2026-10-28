"""Read-only: classify the rejected claims logged by blast_radius.py. Usage: classify_rejections.py <jsonl>...
Categories: article-only quote mismatch (quote fails only the verbatim check, and matches the cited
passage when a/an/the are interchangeable word for word); other quote mismatch (verbatim fails
otherwise); other deterministic condition (quote is verbatim, another check fails); no cited chunk."""
import json, subprocess, sys
from collections import Counter, defaultdict
cat, examples = Counter(), defaultdict(list)
seen = set()
pages = dict(l.split("|", 1) for l in subprocess.run(["psql", "-At", "-d", "procedureassist_staging", "-c",
    "select c.id, p.id||' '||p.name from procedure_chunks c join procedures p on p.id=c.procedure_id"],
    capture_output=True, text=True).stdout.splitlines())
for path in sys.argv[1:]:
    raw = [json.loads(l) for l in open(path)]
    for r in raw:
        c = r["claim"]
        key = (path, str(c.get("text")).strip(), str(c.get("quote")).strip(), c.get("chunk_id"))
        dup = key in seen
        seen.add(key)
        f = r["failed"]
        if "cited_chunk" in f:
            k = "no cited chunk / malformed"
        elif "verbatim" in f and r["article_match"] and f == ["verbatim"]:
            k = "article-only quote mismatch"
        elif "verbatim" in f:
            k = "other quote mismatch" + (" (+ other checks)" if len(f) > 1 else "")
        else:
            k = "other condition: " + ",".join(f)
        cat[(path.rsplit("/", 1)[-1], k, "duplicate" if dup else "unique")] += 1
        if not dup:
            examples[k].append((path.rsplit("/", 1)[-1], pages.get(str(c.get("chunk_id")), "?"), c))
    print(f"{path.rsplit('/', 1)[-1]}: {len(raw)} rejected claim records")
print()
for (f, k, d), n in sorted(cat.items()):
    print(f"{n:3}  {f:32} {d:9} {k}")
for k, items in examples.items():
    print(f"\n### {k} ({len(items)} unique)")
    for f, page, c in items:
        print(f"  [{f}] chunk {c.get('chunk_id')} (page {page})\n     text:  {str(c.get('text'))[:170]!r}\n     quote: {str(c.get('quote'))[:170]!r}")
