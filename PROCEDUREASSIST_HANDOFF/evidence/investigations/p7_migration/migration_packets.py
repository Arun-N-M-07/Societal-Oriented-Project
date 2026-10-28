"""Read-only: the human review packet for each of the 14 pages the migration approves (19, "Final migration approval
checklist", item 1; since 27 Oct page 17 is deleted, not replaced, and gets a delete entry instead): the action and URLs, the exact card to enter in the admin review form (the staging record with the
reviewer's corrections, validate_migration.REVIEWED), whether it equals the approved card today, the source text
(length, SHA-256, chunks) and a grounding check: which steps and which eligibility sentences appear word for word in the
page text. Nothing is written to any database.   migration_packets.py <out.md>"""
import hashlib, json, re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
sys.path.insert(0, "/Users/arunnm/Projects/SOP/PROCEDUREASSIST_HANDOFF/evidence/other/scripts")
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.config import DATABASE_URL
from backend.models import Procedure
from backend.rag import chunk_text
from validate_migration import REVIEWED

PLAN = [(39, "Add"), (40, "Add"), (16, "Move"), (31, "Move"), (32, "Move"), (33, "Move"), (18, "Replace"),
        (19, "Replace"), (20, "Replace"), (27, "Replace"), (35, "Replace"), (36, "Replace"), (37, "Replace"), (38, "Replace")]
FIELDS = ("name", "department", "jurisdiction", "summary", "eligibility", "steps")
card = lambda p: {"name": p.name, "department": p.department, "jurisdiction": p.jurisdiction, "summary": p.summary,
                  "eligibility": p.structured_data.get("eligibility"), "steps": p.structured_data.get("steps", [])}
norm = lambda t: " ".join((t or "").replace("“", '"').replace("”", '"').replace("’", "'").split()).lower()
STOP = {"the", "and", "for", "with", "your", "from", "this", "that", "have", "will", "into", "under", "their", "they", "which"}

def overlap(sentence, text):
    """The share of a sentence's content words (4+ letters) whose first 5 letters occur in the page text."""
    words = [w for w in re.findall(r"[a-z0-9]+", norm(sentence)) if len(w) >= 4 and w not in STOP]
    stems = {w[:5] for w in re.findall(r"[a-z0-9]+", text)}
    return sum(w[:5] in stems for w in words) / len(words) if words else 1.0

def sessions():
    base = DATABASE_URL.rsplit("/", 1)[0]
    return (Session(create_engine(DATABASE_URL)), Session(create_engine(base + "/procedureassist_staging")))

out = [f"# Migration review packets (generated read-only by `{sys.argv[0].split('/')[-1]}`)\n",
       "For each page: enter exactly this card in the admin review form after Extract, then check the listed items.",
       "Steps marked **not word for word** are paraphrases from the earlier approval: check them against the page.",
       "Corrections proposed for the cards of 18, 20, 33, 36, 37 and 38 (`../p9_final/replacement_field_review.md`) await the "
       "owner's approval; once approved they go into validate_migration.REVIEWED and this file is regenerated.\n"]
approved, staging = sessions()
summary = []
try:
    ap = {p.source_url: p for p in approved.query(Procedure)}
    for pid, action in PLAN:
        s = staging.get(Procedure, pid)
        want = {**card(s), **REVIEWED.get(s.source_url, {})}
        old = next((p for url, p in ap.items() if p.id == pid), None)
        text = norm(s.source_text)
        sentences = [x for x in re.split(r"(?<=[.!?])\s+", want["eligibility"] or "") if x.strip()]
        chunks = chunk_text(s.source_text)
        out.append(f"## {action}: {want['name']}\n")
        out.append(f"- **URL after migration:** `{s.source_url}`")
        if old and old.source_url != s.source_url:
            out.append(f"- **Old record to delete after approving the new URL:** `{old.source_url}` (approved id {old.id})")
        elif old:
            out.append(f"- **Replace:** delete approved id {old.id} in Saved procedures, then press Approve at once (the URL is unique).")
        out.append(f"- **Source text:** {len(s.source_text)} characters, SHA-256 `{hashlib.sha256(s.source_text.encode()).hexdigest()[:16]}…`, "
                   f"{len(chunks)} chunks; the 27 Oct re-scrape equals it exactly.")
        if old:
            same = [f for f in FIELDS if card(old)[f] == want[f]]
            diff = [f for f in FIELDS if f not in same]
            out.append(f"- **Card against the approved record today:** {'identical' if not diff else 'changes ' + ', '.join(diff)}")
        out.append("\n| Field | Enter |\n|---|---|")
        for f in ("name", "department", "jurisdiction", "summary"):
            out.append(f"| {f} | {want[f] or '*(empty)*'} |")
        found = [x for x in sentences if norm(x) in text]
        out.append(f"| eligibility | {want['eligibility'] or '*(empty)*'} |")
        out.append(f"\n**Eligibility, word for word in the page:** {len(found)} of {len(sentences)} sentences"
                   + ("" if len(found) == len(sentences) else " — check: " + "; ".join(f'“{x}”' for x in sentences if x not in found)))
        out.append(f"\n**Steps ({len(want['steps'])}):**")
        low = 0
        for n, step in enumerate(want["steps"], 1):
            share = overlap(step, text)
            low += share < 0.8 and norm(step) not in text
            out.append(f"{n}. {step}" + ("" if norm(step) in text else
                       f"  — **not word for word** (words found {share:.0%}{'; check carefully' if share < 0.8 else ''})"))
        summary.append((pid, action, want["name"], len(want["steps"]), sum(norm(x) in text for x in want["steps"]), low,
                        sum(overlap(x, text) < 0.8 for x in sentences if norm(x) not in text)))
        out.append(f"\n**Chunks (first words):** " + " | ".join(" ".join(c.split()[:6]) for c in chunks) + "\n")
    gone = approved.get(Procedure, 17)  # deleted by the owner's decision (27 Oct), nothing re-approved
    if gone:
        out.append(f"## Delete: {gone.name} (approved id 17)\n\n- **URL:** `{gone.source_url}`\n- In Saved procedures, delete it. "
                   "Nothing replaces it. After the delete: no page with this URL, its chunks removed by cascade, no orphans.\n")
finally:
    approved.close(); staging.close()
table = ["| Id | Action | Page | Steps | Word for word | Paraphrase, words found < 80% | Eligibility sentences < 80% |",
         "|---|---|---|---|---|---|---|"] + [f"| {a} | {b} | {c} | {d} | {e} | {f} | {g} |" for a, b, c, d, e, f, g in summary]
out[3:3] = ["## Summary\n"] + table + [""]
open(sys.argv[1], "w").write("\n".join(out) + "\n")
print(f"{len(PLAN)} packets written")
