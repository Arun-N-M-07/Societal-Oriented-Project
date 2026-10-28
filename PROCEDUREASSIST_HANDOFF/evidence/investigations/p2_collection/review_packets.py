"""Read-only: prepare a human review packet for each candidate official URL using the app's own ingestion functions,
exactly as Extract does (scraper.scrape_url, then extractor.extract_procedure). Nothing is saved, approved or embedded;
the reviewer still decides every field in the admin page. For each page it records the draft card, the source text,
its chunks (rag.chunk_text) and simple quality flags: very short paragraphs (labels), chunk cuts that are not at a
sentence end, and text shared with a stored procedure.
    review_packets.py <out.json> <url> [<url> ...]"""
import json, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend.database import SessionLocal
from backend.extractor import extract_procedure
from backend.models import Procedure
from backend.rag import CHUNK_SIZE, chunk_text
from backend.scraper import scrape_url

out, packets = sys.argv[1], {}
with SessionLocal() as db:
    stored = {p.source_url: set(p.source_text.split("\n\n")) for p in db.query(Procedure)}
for url in sys.argv[2:]:
    packet = {"url": url}
    try:
        source = scrape_url(url)
        draft = extract_procedure(source.source_text, source.source_url)
        blocks = source.source_text.split("\n\n")
        chunks = chunk_text(source.source_text)
        shared = {u: len(set(blocks) & b) for u, b in stored.items() if len(set(blocks) & b) >= 3}
        packet.update({
            "final_url": source.source_url, "draft": draft.model_dump(), "source_text": source.source_text,
            "chunks": chunks,
            "flags": {
                "label_paragraphs": [b for b in blocks if len(b.split()) <= 2],
                "long_paragraphs_cut_mid_sentence": sum(len(b) > CHUNK_SIZE for b in blocks),
                "paragraphs_shared_with_stored_pages": shared,
            },
        })
        print(f"OK   {url}\n     draft name {draft.name!r} | {draft.jurisdiction} | {len(draft.steps)} steps | "
              f"{len(source.source_text)} chars, {len(chunks)} chunks | flags: "
              f"{len(packet['flags']['label_paragraphs'])} labels, {packet['flags']['long_paragraphs_cut_mid_sentence']} long, "
              f"shared {shared}", flush=True)
    except Exception as error:
        packet["error"] = f"{type(error).__name__}: {error}"
        print(f"FAIL {url}\n     {packet['error']}", flush=True)
    packets[url] = packet
json.dump(packets, open(out, "w"), indent=1, ensure_ascii=False)
