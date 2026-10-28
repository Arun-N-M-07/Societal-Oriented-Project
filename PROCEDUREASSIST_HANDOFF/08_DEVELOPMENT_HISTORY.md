# 08 — Development history

## Git milestones (branch `arun-nm`, main branch `main`)

| Date | Commit | What it added |
|---|---|---|
| 2026-09-22 | `f2f1fd1` | Folder structure |
| 2026-09-25 | `44c69c1` … `c06c115` | Backend foundation, procedure model and saving, static and rendered scraper, Qwen extraction client ("50% checkpoint") |
| 2026-10-15 | `62e3540` … `81f2a4f` | Hardening of ingestion, validation and provenance; isolated DB tests; admin authentication; admin list, delete and read-only APIs; chunking and embedding with pgvector; identification; verified follow-up answers; citizen UI; the negation check; release readiness; README limitations |
| 2026-10-16 | `6ed7790` | MVP |
| 2026-10-21 | `745af41` | Maintenance |
| 2026-10-22 | `5e03dff` | Voice input (Indic-Transcribe Flex) |
| 2026-10-23 | `3491415` | "staging": the last commit. Everything below it is uncommitted. |

## Uncommitted work on top of `3491415` (as of 23 Oct 2026)

This work was done in Claude Code sessions and is **not committed**. Commit only when the owner asks.

### Reliability rounds before 23 Oct
These rounds led up to the "Final correctness pass" and changed the following:
- **Per-claim citations.** A claim answered from a related page (e.g. the fee table) carries that page's ID and link (`GuidanceClaim.procedure_id`/`source_url`). Answers are flagged `partial`.
- **Completion from related pages** (`answer_from_naming_pages`).
- **Clarification** when a question names no service. Tamil, Romanized and mixed queries are normalised.
- **Applicant-type fix.** A citizen asking about their own duplicate licence used to get the driving-school fee. The model's own check was unreliable (3/3 wrong on the same input), so it was replaced by a deterministic rule (`APPLICANT_LIMIT`, `_for_the_asker`).
- **Money rule.** Every amount in the quote must be in the claim, so "an additional Rs. 300" that drops the extra Rs. 1,000 is rejected. A fee row's label alone is shown as the official row.
- **Polling-booth answers in order.** The answer prompt asks for steps in official order from the first step.
- **VVPAT.** A question scored 0.522, just below the 0.53 threshold. An abbreviation used by exactly one page now decides a near miss.
- **Scraper menu filter** (`is_menu`) for the income-tax site menus.
- **Evaluation script.** It classifies each outcome and stage. A 27-question held-out set (`fixtures/evaluation/heldout.json`) was added; it is untracked in Git and was never used for tuning.
- **Result of that round:** 73/80 and 23/27 with 0 incorrect answers. Before it: 74/80 with 1 incorrect.

### Source audit, 23 Oct 2026
Covered in detail in `04_AUDIT_HISTORY.md` and `06_SOURCE_URL_AUDIT.md`.
- **Scraper.** Keeps text in `div`, `span` and `summary` tags. Keeps each table row as one paragraph. Gives fee sub-rows their numbered parent row.
- **Chunker.** A heading-aware chunk start.
- **Verification.**
  - The money rule now works per sentence or row.
  - Amounts written as words such as "twenty thousand rupees" are recognised.
  - Quotes may not open with a back-reference ("In such cases").
  - A claim must keep the document kind its quote is about.
- **Identification.** The named-page tie rule.
- **Staging database.** `procedureassist_staging` was built with re-scraped and added sources. The approved database was not changed.
- **Work was split across two sessions.** Two Claude sessions worked on the same tree on 23 Oct: the original and a fork. They agreed who owned what. Every change is recorded in `11_DECISION_LOG.md`.

## Files changed since `3491415` (`git status`)
**Modified:**
- `README.md`
- backend:
  - `backend/procedure_search.py`
  - `backend/rag.py`
  - `backend/routes.py`
  - `backend/schemas.py`
  - `backend/scraper.py`
- frontend:
  - `frontend/src/CitizenPage.tsx`
  - `frontend/src/CitizenPage.test.tsx`
  - `frontend/src/api.ts`
- scripts:
  - `scripts/evaluate_answers.py`
  - `scripts/evaluate_needs.py`
- tests:
  - `tests/db_support.py`
  - `tests/test_guidance.py`
  - `tests/test_identify.py`
  - `tests/test_rag.py`
  - `tests/test_scraper.py`

**Untracked:**
- `fixtures/evaluation/heldout.json`
- `PROCEDUREASSIST_HANDOFF/` (this folder)

Nothing is staged.
