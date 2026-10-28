# Stage 1 RAG audit evidence (25 Oct 2026)

Raw evidence for `12_RAG_RELIABILITY_AUDIT.md`. Every file below except this README and `SHA256SUMS.txt` is a byte-identical copy of the original in the temporary session folder (see `SHA256SUMS.txt`).

**Code state when produced:**
- `backend/rag.py` `2eb8f9ff…` (H1 plus number-word fix);
- `tests/test_guidance.py` `97cc1f7b…`;
- uncommitted, on top of `3491415`.

**Database:** all probes read `procedureassist_staging` (26 pages, 140 chunks, procedures md5 `8aba737f…`, chunks md5 `93000b69…`). Nothing was written to either database.

| File | What it is | Produced by |
|---|---|---|
| `scripts/recall.py` → `recall_staging.txt` | Within-page rank of the first evidence-bearing chunk for 81 English fixture cases (main + held-out) | Original script |
| `scripts/probe.py` → `probe_staging.jsonl`, `probe_staging.err` (empty) | The 42-question audit probe: `/api/identify` and `/api/guidance` as the citizen page calls them, top-3 page scores, evidence rank on the expected page, final claims. Exit code 0. | Original script |
| `miss_traces.txt` | Stage-by-stage traces of six weak answers | `evidence/investigations/h4/scripts/trace_h4.py` (already preserved), one run per question |
| `chunk_context.txt` | Heading context of every staging chunk, and chunk boundaries that cut a sentence (both databases) | **Inline commands, not saved as files.** Transcribed below. |
| `tie_scores.txt` | Page scores and `classify` outcome for the remaining close calls | **Inline command, not saved as a file.** Transcribed below. |

**Not saved to any file:** the abbreviation-override check (`_decide` on "What is the fee to renew the RC of a motorcycle?"). Its output exists only in the session transcript. It is reported in `12`, W2, with the command below to reproduce it.

## How to reproduce (read-only)
Run from the repository root with the staging URL in the environment. `.env` is not edited; the name is replaced in-process:
```bash
export DATABASE_URL=$(.venv/bin/python -c "from backend.config import DATABASE_URL as u; print(u.rsplit('/',1)[0]+'/procedureassist_staging')")
```
Then:
```bash
.venv/bin/python PROCEDUREASSIST_HANDOFF/evidence/investigations/rag_audit/scripts/recall.py
```
```bash
.venv/bin/python PROCEDUREASSIST_HANDOFF/evidence/investigations/rag_audit/scripts/probe.py > probe.jsonl
```
For a single question, stage by stage:
```bash
.venv/bin/python PROCEDUREASSIST_HANDOFF/evidence/investigations/h4/scripts/trace_h4.py "<question>" 1
```

Run one Ollama workload at a time. Answers come from `qwen3:8b` at temperature 0, so a re-run may still differ slightly; retrieval and page scores are deterministic for the same data.

## Inline commands, transcribed from the session

These are the commands as they were run on 25 Oct. They are transcriptions for reproduction, not original files.

**`chunk_context.txt`, part 1** (heading context; output to stdout):
```python
import sys, subprocess
sys.path.insert(0, ".")
from backend.rag import _is_heading
rows = subprocess.run(["psql", "-At", "-F", "\x1f", "-R", "\x1e", "-d", "procedureassist_staging", "-c",
                       "select procedure_id, chunk_index, id, content from procedure_chunks order by procedure_id, chunk_index"],
                      capture_output=True, text=True).stdout.split("\x1e")
pages = {}
for r in rows:
    if r.strip():
        pid, idx, cid, content = r.split("\x1f", 3)
        pages.setdefault(int(pid), []).append((int(idx), int(cid), content))
stats = {"later chunks": 0, "start at heading": 0, "repeat previous paragraph (overlap)": 0, "start mid-section": 0}
mid = []
for pid, chunks in pages.items():
    for (i, cid, content), (_, _, prev) in zip(chunks[1:], chunks[:-1]):
        stats["later chunks"] += 1
        first = content.split("\n\n")[0]
        if _is_heading(first):
            stats["start at heading"] += 1
        elif first in prev.split("\n\n"):
            stats["repeat previous paragraph (overlap)"] += 1
        else:
            stats["start mid-section"] += 1
            heads = [b for b in prev.split("\n\n") if _is_heading(b)]
            mid.append((pid, cid, first[:70], heads[-1][:60] if heads else "-"))
print(stats)
print("chunks starting mid-section (page, chunk, first paragraph, last heading in previous chunk):")
for m in mid:
    print("  ", m)
```
**`chunk_context.txt`, part 2** (sentences cut across a boundary; appended):
```python
import subprocess
for db in ("procedureassist_staging", "procedureassist"):
    rows = subprocess.run(["psql", "-At", "-F", "\x1f", "-R", "\x1e", "-d", db, "-c",
                           "select procedure_id, chunk_index, id, content from procedure_chunks order by procedure_id, chunk_index"],
                          capture_output=True, text=True).stdout.split("\x1e")
    pages = {}
    for r in rows:
        if r.strip():
            pid, idx, cid, content = r.split("\x1f", 3)
            pages.setdefault(int(pid), []).append((int(cid), content))
    print(f"\n== {db}: sentences cut across a chunk boundary")
    n = 0
    for pid, chunks in pages.items():
        for (pcid, prev), (cid, cur) in zip(chunks, chunks[1:]):
            last, first = prev.split("\n\n")[-1], cur.split("\n\n")[0]
            if not last.rstrip().endswith((".", "?", ":", "!", "-", ")")) and first not in prev and len(last) > 200:
                n += 1
                print(f"  page {pid}: chunk {pcid} ends '...{last[-60:]}' | chunk {cid} starts '{first[:60]}...'")
    print(f"  total: {n}")
```
**`tie_scores.txt`** (DATABASE_URL = staging):
```python
import sys; sys.path.insert(0, ".")
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure
from backend.procedure_search import rank_procedures, classify
with SessionLocal() as db:
    names = {p.id: p.name for p in db.query(Procedure)}
    for q, want in [("I have a learner's licence and want my first full driving licence", "Permanent"),
                    ("I live abroad. How do I register to vote?", "Overseas"), ("I just turned 18 and want to vote.", "Register to Vote"),
                    ("Which form is used to correct entries in the electoral roll?", "Register to Vote"),
                    ("What is the fee for renewing my driving licence after the grace period?", "Fees"),
                    ("What's the charge to fix my address in Aadhaar at the post office?", "Post Offices"),
                    ("How do I get my name on the voters list?", "Register to Vote")]:
        r = rank_procedures(db, rag.embed_texts([q], query=True)[0])
        print(f"{q[:62]!r:66} {[(names[i][:26], round(s, 3)) for i, s in r]} -> {classify(r)[0]} (wanted: {want})")
```
**Abbreviation override (W2), not saved; reproduce with** (DATABASE_URL = staging):
```python
import sys; sys.path.insert(0, ".")
from backend import rag
from backend.database import SessionLocal
from backend.models import Procedure
from backend.procedure_search import rank_procedures, classify, abbreviates, ACRONYM, _decide
with SessionLocal() as db:
    q = "What is the fee to renew the RC of a motorcycle?"
    v = rag.embed_texts([q], query=True)[0]
    names = {p.id: p.name for p in db.query(Procedure)}
    ranked = rank_procedures(db, v)
    print([(names[i], round(s, 3)) for i, s in ranked], classify(ranked))
    print([names[i] for i in names if abbreviates("RC", names[i])])
    print(_decide(db, v, q))
```
The session output was:
- ranked: 39 (0.654), 27 (0.539), 28 (0.530);
- `classify` → `('matched', [39])`;
- "RC" abbreviates *Renewal of Vehicle Registration Certificate* and *REV-101 Community Certificate*;
- `_decide` → matched *Renewal of Vehicle Registration Certificate* (page 28).
