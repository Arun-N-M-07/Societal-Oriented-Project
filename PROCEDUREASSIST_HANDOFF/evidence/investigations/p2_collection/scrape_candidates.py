"""Read-only: run the app's own scrape_url (the admin Extract path: allow-list, safe fetch, browser fallback, clean_html)
on candidate official URLs, and report what the generic workflow would get. Nothing is stored; no model is called.
    scrape_candidates.py <out.json> <url> [<url> ...]"""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend.rag import chunk_text
from backend.scraper import scrape_url

out, results = sys.argv[1], {}
for url in sys.argv[2:]:
    try:
        r = scrape_url(url)
        blocks = r.source_text.split("\n\n")
        results[url] = {"final_url": r.source_url, "chars": len(r.source_text), "paragraphs": len(blocks),
                        "chunks": len(chunk_text(r.source_text)), "text": r.source_text}
        print(f"OK   {url}\n     final {r.source_url} | {len(r.source_text)} chars, {len(blocks)} paragraphs, "
              f"{results[url]['chunks']} chunks | {r.source_text[:160]!r}", flush=True)
    except Exception as error:
        results[url] = {"error": f"{type(error).__name__}: {error}"}
        print(f"FAIL {url}\n     {type(error).__name__}: {error}", flush=True)
json.dump(results, open(out, "w"), indent=1, ensure_ascii=False)
