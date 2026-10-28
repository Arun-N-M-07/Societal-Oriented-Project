"""Read-only audit of every stored source: live fetch vs stored text, chunks, embeddings."""
import json, re, sys
from collections import Counter
from urllib.parse import urljoin, urlsplit
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
import httpx, numpy as np
from bs4 import BeautifulSoup
from backend.database import SessionLocal
from backend.models import Procedure, ProcedureChunk
from backend.rag import chunk_text, embed_texts
from backend import scraper

OUT = sys.argv[1]
report = []
with SessionLocal() as db:
    procs = db.query(Procedure).order_by(Procedure.id).all()
    all_chunks = db.query(ProcedureChunk).order_by(ProcedureChunk.procedure_id, ProcedureChunk.chunk_index).all()
    content_owner = {}
    for c in all_chunks:
        content_owner.setdefault(c.content, []).append((c.procedure_id, c.id))
    for p in procs:
        r = {"id": p.id, "url": p.source_url, "name": p.name, "department": p.department,
             "stored_chars": len(p.source_text), "structured_keys": sorted(p.structured_data)}
        # redirect chain
        try:
            resp = httpx.get(p.source_url, follow_redirects=True, timeout=25, headers={"User-Agent": scraper.USER_AGENT})
            r["http_status"] = resp.status_code
            r["redirects"] = [str(h.url) + f" ({h.status_code})" for h in resp.history]
            r["final_url"] = str(resp.url)
            r["content_type"] = resp.headers.get("content-type")
        except Exception as e:
            r["http_status"] = f"error {type(e).__name__}: {e}"
        # live extraction with the app's scraper
        html, how = None, None
        try:
            final, html = scraper.fetch_static_html(p.source_url); how = "static"
            text = scraper.clean_html(html)
            if not scraper.is_source_text_usable(text):
                final, html = scraper.fetch_rendered_html(p.source_url); how = "rendered"
                text = scraper.clean_html(html)
        except Exception as e:
            text = None; r["scrape_error"] = f"{type(e).__name__}: {e}"
        r["fetched_with"] = how
        if html:
            soup = BeautifulSoup(html, "html.parser")
            r["title"] = soup.title.get_text(" ", strip=True) if soup.title else None
            h1 = soup.find("h1"); r["h1"] = h1.get_text(" ", strip=True) if h1 else None
            host = urlsplit(p.source_url).hostname
            links = []
            for a in soup.find_all("a", href=True):
                u = urljoin(final, a["href"]).split("#")[0]
                if urlsplit(u).scheme in ("http", "https"):
                    links.append((" ".join(a.get_text(" ", strip=True).split())[:80], u))
            r["links"] = list(dict.fromkeys(links))
        stored_blocks = p.source_text.split("\n\n")
        if text is not None:
            live_blocks = text.split("\n\n")
            r["live_chars"] = len(text)
            r["identical"] = text == p.source_text
            r["stored_only"] = [b for b in stored_blocks if b not in live_blocks]
            r["live_only"] = [b for b in live_blocks if b not in stored_blocks]
        # chunk integrity
        mine = [c for c in all_chunks if c.procedure_id == p.id]
        expected = chunk_text(p.source_text)
        r["chunks"] = len(mine)
        r["chunk_ids"] = [c.id for c in mine]
        r["chunks_match_text"] = [c.content for c in mine] == expected
        r["chunk_index_contiguous"] = [c.chunk_index for c in mine] == list(range(len(mine)))
        vecs = embed_texts([c.content for c in mine])
        sims = [float(np.dot(a, np.array(c.embedding)) / np.linalg.norm(a) / np.linalg.norm(c.embedding)) for a, c in zip(np.array(vecs), mine)]
        r["embedding_min_cos_vs_fresh"] = round(min(sims), 4)
        r["dup_chunks_elsewhere"] = [(c.id, [o for o in content_owner[c.content] if o[1] != c.id]) for c in mine if len(content_owner[c.content]) > 1]
        r["block_repeats"] = [b[:80] for b, n in Counter(stored_blocks).items() if n > 1]
        r["menu_like_blocks"] = [b[:100] for b in stored_blocks if scraper.is_menu(b)]
        r["source_text"] = p.source_text
        r["live_text"] = text
        report.append(r)
        print(p.id, r.get("http_status"), r.get("final_url") != p.source_url and r.get("final_url"), how, "identical" if r.get("identical") else f"diff -{len(r.get('stored_only',[]))}/+{len(r.get('live_only',[]))}", "chunksOK" if r["chunks_match_text"] else "CHUNK MISMATCH", r["embedding_min_cos_vs_fresh"], r.get("title"), flush=True)
json.dump(report, open(OUT, "w"), indent=1, ensure_ascii=False)
