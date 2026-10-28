"""Read-only: re-scrape the 11 candidate URLs (20, "Phase 2") with the app's scraper and compare each text with the
26 Oct review packet (p2_collection/review_packets.json). No model, no database write.   rescrape_candidates.py <out.json>"""
import hashlib, json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend.scraper import require_official, scrape_url
PACKETS = "/Users/arunnm/Projects/SOP/PROCEDUREASSIST_HANDOFF/evidence/investigations/p2_collection/review_packets.json"
packets = json.load(open(PACKETS))
result = {}
for n, (url, packet) in enumerate(packets.items(), 1):
    entry = {"url": url}
    try:
        require_official(url)
        page = scrape_url(url)
        old = packet.get("source_text", "")
        ob, nb = old.split("\n\n"), page.source_text.split("\n\n")
        entry |= {"final_url": page.source_url, "chars": len(page.source_text), "sha256": hashlib.sha256(page.source_text.encode()).hexdigest(),
                  "same_as_26_oct": page.source_text == old, "blocks_removed": [b for b in ob if b not in nb],
                  "blocks_added": [b for b in nb if b not in ob], "text": page.source_text}
        print(f"N{n:<2} OK   {url[:80]:80} {len(old)} -> {len(page.source_text)} chars; "
              f"{'identical' if entry['same_as_26_oct'] else f'-{len(entry["blocks_removed"])} +{len(entry["blocks_added"])} blocks'}", flush=True)
    except Exception as error:
        entry["error"] = f"{type(error).__name__}: {error}"
        print(f"N{n:<2} FAIL {url[:80]:80} {entry['error'][:120]}", flush=True)
    result[url] = entry
json.dump(result, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
