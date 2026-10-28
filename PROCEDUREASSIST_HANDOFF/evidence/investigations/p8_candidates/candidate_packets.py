"""Read-only: a review packet for each of the 11 candidate procedures (20, "Phase 2"): the model's 26 Oct draft card from
the unmodified Extract path (p2_collection/review_packets.json; the 27 Oct re-scrape equals each text exactly), with a
grounding check of every step and eligibility sentence against the page text, the paragraphs shared with stored pages, and
the 26 Oct reviewer notes. A human decides every field; nothing is saved.   candidate_packets.py <out.md>"""
import json, re, sys
# The same checks as p7_migration/migration_packets.py.
norm = lambda t: " ".join((t or "").replace("“", '"').replace("”", '"').replace("’", "'").split()).lower()
STOP = {"the", "and", "for", "with", "your", "from", "this", "that", "have", "will", "into", "under", "their", "they", "which"}

def overlap(sentence, text):
    """The share of a sentence's content words (4+ letters) whose first 5 letters occur in the page text."""
    words = [w for w in re.findall(r"[a-z0-9]+", norm(sentence)) if len(w) >= 4 and w not in STOP]
    stems = {w[:5] for w in re.findall(r"[a-z0-9]+", text)}
    return sum(w[:5] in stems for w in words) / len(words) if words else 1.0
BASE = "/Users/arunnm/Projects/SOP/PROCEDUREASSIST_HANDOFF/evidence/investigations/"
packets = json.load(open(BASE + "p2_collection/review_packets.json"))
fresh = json.load(open(BASE + "p8_candidates/rescrape_candidates.json"))
out = ["# Candidate procedures: review packets (generated read-only)\n",
       "Drafts are the model's; the reviewer decides every field in the admin page. Steps and sentences marked "
       "**not word for word** need checking against the page.\n"]
for n, (url, p) in enumerate(packets.items(), 1):
    d, text = p["draft"], norm(p["source_text"])
    same = fresh.get(url, {}).get("same_as_26_oct")
    out.append(f"## N{n}: {d['name']}\n")
    out.append(f"- **URL:** `{url}`" + (f" (final `{p['final_url']}`)" if p.get("final_url") and p["final_url"] != url else ""))
    out.append(f"- **Text:** {len(p['source_text'])} characters, {len(p['chunks'])} chunks; 27 Oct re-scrape "
               f"{'identical' if same else 'DIFFERENT — re-check'}")
    shared = p["flags"]["paragraphs_shared_with_stored_pages"]
    out.append(f"- **Paragraphs shared with stored pages:** {', '.join(f'{k} ({v})' for k, v in shared.items()) or 'none'}")
    out.append(f"- **Draft:** department *{d['department']}*; jurisdiction *{d['jurisdiction']}*")
    out.append(f"- **Summary (draft):** {d['summary']}")
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", d.get("eligibility") or "") if x.strip()]
    out.append(f"- **Eligibility (draft):** {d.get('eligibility') or '*(empty)*'}")
    for x in sentences:
        if norm(x) not in text:
            out.append(f"  - not word for word (words found {overlap(x, p['source_text']):.0%}): “{x}”")
    out.append(f"\n**Steps (draft, {len(d['steps'])}):**")
    for k, step in enumerate(d["steps"], 1):
        share = overlap(step, p["source_text"])
        out.append(f"{k}. {step}" + ("" if norm(step) in text else
                   f"  — not word for word (words found {share:.0%}{'; **check carefully**' if share < 0.8 else ''})"))
    out.append("")
open(sys.argv[1], "w").write("\n".join(out) + "\n")
print(len(packets), "packets")
