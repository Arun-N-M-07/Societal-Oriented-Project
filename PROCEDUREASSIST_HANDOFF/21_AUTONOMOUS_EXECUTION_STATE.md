# 21 — Autonomous execution state

**Current brief:** "Final Autonomous Execution, Procedure Approval, Database Correction & Reliability Verification" (27 Oct 2026, from 10:38 IST).
**Previous brief** (02:20–09:40 the same day): "Autonomous Final Reliability, Database Correction & Generalisation". Its log is kept below, from "Previous brief: phases".
**Last updated:** 27 Oct 2026, 19:30 IST.
**Current phase (28 Oct 10:45): the original execution is complete up to the owner-approval boundary;** see the task table. Earlier: **the session stopped for a fresh-account handoff.** The brief was interrupted at ~11:30 during Phase 3, before any approval. A documentation-only handoff then ran from 18:50 (brief "Complete Project Context Transfer and Fresh-Account Handoff").
**Exact next action** for the new session:
1. Read `00_START_HERE.md` and `15_NEXT_SESSION_PROMPT.md`.
2. Verify the state below.
3. Do `10_PENDING_WORK.md`, P1: the evaluation labels for the changed collection.
4. Then P2: test and approve the candidates, starting with N1, N3, N4 and N8 (`evidence/investigations/p9_final/candidate_review_27oct.md`).

To resume in a new session: read this file, then check `git status`, the database checksums (below) and the newest folders in `evidence/`, before repeating anything.

## Current brief: the owner's decisions
- **Page 17 is deleted, not replaced.** This is "REV-101 Community Certificate" (planned name "e-Sevai FAQ: CAN and certificate documents"), `https://tnesevai.tn.gov.in/Citizen/FAQ.html`. The production deletion still needs the owner's separate approval.
- **The five candidates N1, N3, N4, N8 and N10:** Claude reviews them and approves them through the admin workflow. This is delegated. N2, N5, N6, N7, N9 and N11 are not added.
- **Page 39's step:** "Refer to the fee table to identify the applicable fee for the relevant vehicle-related service."
- **The rest of the migration is prepared and tested only:** the deletion, 8 replacements, 4 moves and 2 additions.

## Current brief: task status (28 Oct 2026, 10:45 IST)
| Task (brief section) | Status | Result / where |
|---|---|---|
| §2 Reconnaissance | **COMPLETE** | "Reconnaissance"; re-verified 27 Oct 21:28 |
| §3 Page 17: record, chunks, foreign keys, deletion plan | **COMPLETE** | One cascade foreign key; nothing else refers to a procedure |
| §3 Page 17: deletion tested on an isolated copy (rolled back) | **COMPLETE** | Scratch: 24→23 pages, 122→118 chunks, 0 orphans, others unchanged |
| §3 Page 17: staging rehearsal | **COMPLETE** | Staging deleted 27 Oct 10:50 (backup first; backup restore-tested 21:30) |
| §3.4 Retrieval after the deletion | **COMPLETE** | Staging: the 4 after-deletion cases give no match (no CAN steps, no card). With N8: birth/death certificates get the right page; other TN certificates abstain with no card (`p9_final` runs) |
| §3 Page 17: delete from the approved database | **REQUIRES OWNER APPROVAL** | Still stored in approved |
| §4 Revised migration (deletion, 8 replacements, 4 moves, 2 additions, 11 untouched) | **COMPLETE (prepared)** | Doc 19 checklist; validator and packets updated (self-test 12/12); field review done (`p9_final/replacement_field_review.md`); ID 33 freshness checked |
| §4 Card corrections from the field review (18, 20, 33, 36, 37, 38) | **REQUIRES OWNER APPROVAL** | Proposed only |
| §4 Execute the production migration | **REQUIRES OWNER APPROVAL** | Not done. Target after it: 28 pages / 146 chunks |
| §5 N3, N4, N8 | **APPROVED** (28 Oct 09:33–09:34) | Approved ids 39–41, staging ids 41–43; records, chunks and embeddings verified; unrelated rows byte-identical |
| §5 N1 Instant e-PAN | **DEFERRED** | A misleading verified answer path for lost/duplicate PAN questions (`11` #57) |
| §5 N10 New ration card | **DEFERRED** | 2008-era submission route |
| §5.5 N2, N5, N6, N7, N9, N11 | **DEFERRED** (owner) | Not added |
| §6 Identification improvements preserved | **COMPLETE** | One general fix only (`11` #56); no threshold, LLM layer or page-specific rule |
| §7 Card safety (16 topics) | **COMPLETE** | `p9_scratch_candidates/scratch_card_safety.txt` (production copy). Production still shows page 17's CAN steps for income and community certificate applications until the deletion |
| §8 P1-3 | **COMPLETE** | `10` P3.2 |
| §9 Tests and evaluation | **COMPLETE** | Backend 252 OK; frontend 67; type check; build; full suite `p9_final` (18 runs) and ingestion acceptance (below) |
| §10 Port 8000 | **COMPLETE** (28 Oct 10:31) | PID 75965 stopped; PID 89049 serves the current code (`evidence/test_results/p9_port8000_restart.txt`) |
| §11 Migration approval packet | **COMPLETE (prepared)** | Doc 19 checklist and `22` (final report). The maintenance window and people are left for the owner |
| §12 Documentation | **COMPLETE** | Docs 03, 07, 10, 11, 19, 21, 22, packets |
| Handoff documentation brief | **PAUSED** | Resume after this task: the final account-transfer audit and `15_NEXT_SESSION_PROMPT.md` |

## Reconnaissance (10:38–10:55)
- **Git:**
  - branch `arun-nm`, HEAD `3491415` ("staging");
  - 38 status entries (31 modified, 7 untracked); no stash; nothing staged;
  - `backend/`, `scripts/` and `fixtures/` equal the `snap_p7_final` snapshot byte for byte, so nothing changed since the previous brief.
- **`.env`:** modified 15 Oct 08:38:46 (untouched).
- **Databases:**

  | Database | Pages | Chunks | md5 (procedures / chunks) |
  |---|---|---|---|
  | Approved | 24 | 122 | `016980ee…` / `3e45c78f…` (unchanged) |
  | Staging | 26 | 140 | `8aba737f…` / `93000b69…` (unchanged) |
  | Test | empty | — | — |

- **Schema:** two tables.
  - The only foreign key is `procedure_chunks.procedure_id` → `procedures.id`, `ON DELETE CASCADE`.
  - `source_url` is unique, and so is (`procedure_id`, `chunk_index`).
  - Nothing else refers to a procedure, so deleting one removes exactly its own chunks.
- **Page 17:**
  - approved: id 17, "REV-101 Community Certificate", 4 chunks (ids 33–36);
  - staging: the same id and name, 6 chunks (ids 507–512, the re-scraped text).
- **Admin workflow:**
  - `POST /api/admin/extract`: scrape, model draft, and a provenance token valid for 2 hours;
  - `POST /api/admin/procedures`: token check, chunking and embedding, then save;
  - `DELETE /api/admin/procedures/{id}`.
  - There is no edit route.
- **Port 8000:**
  - PID 75965, `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`, working directory the repository, parent `launchd`;
  - started Fri 23 Oct 22:51 by an earlier Claude session, so it serves code older than every change since;
  - its log, in that session's scratchpad, shows its last request at 25 Oct 15:23 (a health check);
  - no open connections; no frontend dev server is running.
- **Other Claude session** PID 17576 (started 24 Oct 01:40): idle, not used.
- **Sleep:** `caffeinate -dimsu -w 51627` (PID 28149) is still running.

## Resumed 27 Oct 21:28: the original execution continued (owner's message "Resume Interrupted Autonomous Execution")
- **The handoff documentation is paused.** The docs already updated are kept. The handoff audit and `15_NEXT_SESSION_PROMPT.md` come after this task.
- **State re-verified at 21:28 (read-only):**
  - Git: 43 entries, HEAD `3491415`; `.env` from 15 Oct.
  - Databases as in the table below. No candidate URL is stored anywhere; page 17 is present only in approved and in the scratch copy.
  - Both 10:46 dumps exist; `pg_restore -l` gives dbname `procedureassist_staging` / `procedureassist`, 24 TOC entries each.
  - The only fixture differences from `snap_p7_final` are the two relabels.
- **Done since 21:28:**

  | Time | Work | Result / evidence |
  |---|---|---|
  | 21:29 | Remaining "replace page 17" statements annotated | Docs 03, 18, 19 (§A), 20, 21 (old log), 22 (header, §4, §10, §14) and the migration packet |
  | 21:30 | **Restore check of the staging dump** into a new scratch database `procedureassist_restorecheck_staging`; **then dropped** (only that name) | 26 / 140, `8aba737f…` / `93000b69…`: equal to staging before the deletion (`evidence/database/restore_check_staging_27oct.txt`) |
  | 21:31 | **Evaluation labels for the changed collection** (designed earlier; `10` P1.1–P1.2), detailed below the table | Dry check: no configuration has a case expecting a page that is not stored |
  | 21:34 | Snapshot `snap_p9_labels` (scratchpad); **suite started**: staging + approved, all sets | Output: `evidence/evaluations/p9_baseline/` |
  | 21:35 | ID 33 live page, read-only scrape | Identical to staging; still the AY 2025–26 guide (`p9_final/page33_freshness_27oct.txt`) |
  | 21:30–21:45 | **Field review** of the 8 replacements, 33, 39 and 40 | Corrections proposed for 18, 20, 33, 36, 37, 38; none needed for 19, 27, 35; 39 and 40 as decided (`p9_final/replacement_field_review.md`). **Owner approval pending** |
  | 21:46 | `validate_migration.py` and its self-test updated | Page 17 entry removed; page 39's step; page count follows the reference. Self-test: **12/12 PASS**, including the faults "page 17 not deleted" and "page 39 step not as decided" (`p9_final/validate_selftest_27oct.txt`) |
  | 21:47 | Validator against approved (read-only) | 24 failed checks, exactly the planned differences (counts, URLs, the 8 replaced texts, 9 re-chunked pages, 4 FAQ-pair checks); the 11 untouched pages pass (`p9_final/validate_approved_premigration_27oct.txt`) |
  | 21:48 | `migration_packets.py` updated (14 packets + a page 17 delete entry); packets regenerated read-only | `p7_migration/migration_review_packets.md` |
  | 22:25 | **Baseline suite finished.** All 18 runs exit 0; both databases' checksums identical before and after | Case by case vs `p7_final`: only planned skips, new cases and 2 deletion improvements on staging (marriage registration certificate; community certificate + DL renewal). Post-deletion cases 4/4 no match. Follow-ups 17/17; probe 0/42 changed (`10` P1.3) |
  | 22:30 | **P1-3 traced** on staging page 19 | The meaning check rejects the run-on quote "fill form 7 … Please fill Form 8 …"; safe abstention (`10` P3.2; `p9_final/p1_3_trace_staging.txt`) |
  | 22:27–22:29 | **N1, N3, N4, N8 approved into `procedureassist_scratch` only** (Extract → reviewed card → Approve; texts' SHA-256 equal to the review) | ids 39–42; chunks equal `chunk_text`; vectors valid; scratch 28 / 145, `a2713efd…` / `18be1afe…` (`p9_final/candidates_scratch_approval.txt`) |
  | 22:30 | Evaluation of the answer sets + card safety on scratch started | `evidence/evaluations/p9_scratch_candidates/` |
  | 22:52 (28 Oct 09:00) | **Scratch results analysed** (case by case vs approved baseline; every change traced) | **N4:** no regression. **N8:** 7 Tamil Nadu certificate false identifications, all abstaining with no card. **N3:** passport-fee choices; lower-case "idp" lost (top-3 limit). **N1:** a misleading card ("register on the e-filing portal with my PAN" → Instant e-PAN), from a code bug |
  | 09:05 | **Code fix:** `procedure_search.acronym_names` ignores one-letter name pieces (the "e" of "e-PAN"). Test added (2 assertions in `test_a_term_inside_a_longer_name_names_it_only_with_another_word_of_the_name`); it failed before the fix | Backend 252 OK |
  | 09:05–09:28 | Scratch re-run with the fix (snapshot `snap_p9_fix`) | Exactly 1 case changed (that one, now correct) of 300 (`p9_scratch_candidates_fix/`) |
  | 09:30 | **Answers behind the new choices** checked | **N1 misleading:** a lost/duplicate PAN question → choice → Instant e-PAN answers "To get a duplicate PAN card, you can apply for an Instant e-PAN…". The page excludes existing PAN holders. **N1 DEFERRED** |
  | 09:31 | 12 adversarial probes (`p9_scratch_candidates_fix/adversarial_probes.txt`) | N8, N3, N4: no claim and no card on any wrong match |
  | 09:33–09:34 | **DELEGATED APPROVAL of N3, N4, N8**: Extract (SHA-256 equal to review) → reviewed card → Approve, into **staging, then the approved database** (`p9_final/candidates_approval_staging_production.txt`) | **Approved: ids 39 (N3), 40 (N4), 41 (N8): 27 pages / 134 chunks**, `750d4dc2…` / `e7fee548…`. **Staging: ids 41, 42, 43: 28 / 146**, `c442a59c…` / `290cf496…`. Chunks equal `chunk_text`; vectors valid; 0 orphans |
  | 09:35 | Unrelated-record check | Approved rows id ≤ 38 and staging rows id ≤ 40, with their chunks: **byte-identical** to before (`016980ee…`/`3e45c78f…`; `96697b50…`/`73da35b3…`) |
  | 09:36 | Validator against approved (read-only) | The 3 new pages pass every check against staging. The same 24 planned migration differences remain; after the migration: **28 pages / 146 chunks** |
  | 09:35 | **Final suite started** (snapshot `snap_p9_fix`; staging and approved, all sets) | `evidence/evaluations/p9_final/` |
  | 10:29 | **Final suite finished** (18 runs, exit 0; databases unchanged by the run) | `p9_final/metrics_summary.txt`; `22` §D. Correct answers up; 0 misleading cards, unsupported or citation failures. Every false identification traced: no card and no claim (`p9_final/staging_regressions_traced.txt`) |
  | 10:31 | **Port 8000 restarted**: PID 75965 → PID 89049 | Health and readiness OK; current code and data (`evidence/test_results/p9_port8000_restart.txt`) |
  | 10:33 | Needs sets: the pre-decided birth-certificate label (`krishnagiri`) applied to the same question in `population.json` and `demo_services.json` | Missed on 27 Oct 21:31; the same label as answers/safety |
  | 10:35 | Frontend 67 passed; strict type check OK; production build OK; backend 252 OK | — |
  | 10:35–10:44 | Ingestion acceptance, twice | 38/40 both runs; the e-PAN fee answer abstains (model writes the question as the claim; the negation rule rejects it) |

  The 21:31 label changes:
  - `requires: tnesevai` on 15 page-17 cases;
  - 4 after-deletion cases (`unless: tnesevai`, safety category "I page 17 deleted");
  - 7 cases relabelled for N1 and N8 (with `requires`);
  - 9 candidate probes in `generalisation.json`;
  - the 2 needs-set CAN cases → `[null]` (staging-only runs).

## Current brief: operations performed (in order; all times IST, 27 Oct)
| Time | Operation | Database or file touched | Result |
|---|---|---|---|
| 10:46 | `pg_dump -Fc procedureassist_staging` | read-only; `/Users/arunnm/Projects/SOP-backups/procedureassist_staging_2026-10-27_before_page17_deletion.dump` | 800,209 bytes, SHA-256 `9616f56c2f666e8d87950328e200ecbb5aa7e237b01cd2ad8617056da332e9b1`; staging then 26 / 140, `8aba737f…` / `93000b69…` |
| 10:46 | `pg_dump -Fc procedureassist` | read-only; `…/procedureassist_2026-10-27_before_candidates.dump` | 700,813 bytes, SHA-256 `20b54b9e1d7fc2af69673bad33c3f0cb85ccba84245978fb69315d22c4dc437d` |
| 10:47 | `createdb procedureassist_scratch`, `CREATE EXTENSION vector`, `pg_restore` of that dump | **new scratch database** | Checksums equal approved (`016980ee…` / `3e45c78f…`). **It still exists** (kept for candidate testing) |
| 10:49 | Page 17 deletion through `DELETE /api/admin/procedures/17` in one transaction, **rolled back** | scratch | 24 → 23, 122 → 118, 0 orphans, others unchanged; after rollback 24 / 122 |
| 10:50 | Page 17 deletion through the same route, **committed** | **staging** | 26 → **25 pages**, 140 → **134 chunks**; new checksums `96697b50b666c5937d9e6bc10186123e` / `73da35b39dc3956bbaed33125ef6f6ca` |
| 10:50–10:51 | `POST /api/admin/extract` for the five candidates (scrape + model draft; nothing saved) | none (texts and tokens in this session's temporary scratchpad, now unusable) | All five texts equal the 26/27 Oct copies |
| ~11:00–11:25 | Evaluation label changes (no run yet) | `scripts/evaluate_answers.py`, `scripts/evaluate_needs.py`, 8 fixtures | See "Files changed" |
| 18:56 | Backend tests, frontend tests, type check | test database only, in rolled-back transactions | 252 OK, 67 passed, OK; test database still empty |

No other database write happened. **The approved database `procedureassist` was never written** (checksums `016980ee…` / `3e45c78f…` at 18:52).

## Current brief: database state at 28 Oct 09:35 (after the delegated approvals)
| Database | Pages | Chunks | md5 procedures / chunks | Note |
|---|---|---|---|---|
| `procedureassist` (approved) | **27** | **134** | `750d4dc2f448e94373f8eb509b339fe2` / `e7fee54863a0304e9455ce09edaf4a69` | + N3, N4, N8 (ids 39–41), 28 Oct 09:33–09:34. The original 24 pages are byte-identical; page 17 is still stored (deletion needs the owner) |
| `procedureassist_staging` | **28** | **146** | `c442a59cbdfbd0af9c49c9a7eb542372` / `290cf4965b0fd93d6f43c472012d151d` | Page 17 deleted (27 Oct 10:50); + N3, N4, N8 (ids 41–43) |
| `procedureassist_scratch` | 28 | 145 | `a2713efd…` / `18be1afe…` | Test copy: approved + N1, N3, N4, N8 (ids 39–42). Drop when no longer needed |
| `procedureassist_test` | 0 | 0 | — | — |

## Current brief: database state at 18:52 on 27 Oct, before the approvals (`evidence/database/db_checksums.sql`)
| Database | Pages | Chunks | md5 procedures / chunks | Note |
|---|---|---|---|---|
| `procedureassist` (approved) | 24 | 122 | `016980eee56654079df99cddfbabaf00` / `3e45c78f7b85623ad6d9468fa9b34171` | Unchanged since 23 Oct |
| `procedureassist_staging` | **25** | **134** | `96697b50b666c5937d9e6bc10186123e` / `73da35b39dc3956bbaed33125ef6f6ca` | Page 17 deleted 10:50; otherwise the migration target |
| `procedureassist_scratch` | 24 | 122 | equal to approved | Restored 10:47; may be dropped when no longer needed (it is not one of the project databases) |
| `procedureassist_test` | 0 | 0 | — | Tests only |

All four: 0 orphan chunks, embeddings 1024 dimensions, no chunk-index gaps.

## Current brief: files changed
| File | Change | Verified |
|---|---|---|
| `backend/procedure_search.py` | **1 line** (28 Oct): `acronym_names` ignores one-letter name pieces (the "e" of "e-PAN") | Unit test (2 assertions; fails without the fix); backend 252 OK; scratch re-run: 1 of 300 cases changed, back to correct |
| `tests/test_identify.py` | 2 assertions for that fix | — |
| `fixtures/evaluation/` (27 Oct 21:31) | Collection-change labels: `requires`/`unless`, after-deletion cases, candidate relabels and probes | Dry check; baseline run |
| `evidence/other/scripts/validate_migration.py`, `validate_migration_selftest.py`, `p7_migration/migration_packets.py` | Page 17 deleted; page 39 step; page count follows the reference | Self-test 12/12 PASS |
| `scripts/evaluate_answers.py` | `at(fragment, url)`: a fixture's URL fragment matches only when no letter or digit follows it, used at every page lookup; `"unless"` skip key | Fragment-by-fragment check: only `psp/Apply` matches differently. **No evaluation run yet** |
| `scripts/evaluate_needs.py` | The same boundary in `correct()` | As above |
| `fixtures/evaluation/{answers,demo_services,heldout,identification_failures,multi_need,population,safety,tamil}.json` | `"passportindia"` → `"psp/Apply"`; `"uidai"` → `"updating-data-on-aadhaar"`. They name the same pages as before; this keeps the labels unambiguous once N3 or N4 is stored | JSON valid |
| `PROCEDUREASSIST_HANDOFF/evidence/investigations/p9_final/` | New: `admin_workflow.py` (the admin routes in-process; refuses deletes in approved and approvals there except the five delegated URLs), the two page-17 outputs, `candidate_review_27oct.md`, `candidate_cards/` | Used for the staging and scratch operations above |
| Handoff docs | This file; the evening handoff updated `00`, `01`, `02`, `05`, `07`, `08`, `09`, `10`, `11`, `19`, `22` and the packets, and created `15_NEXT_SESSION_PROMPT.md` | — |

**Not changed:** application code (`backend/`, `frontend/`), tests, `.env`, Git history. Nothing committed, nothing pushed.

## Current brief: do not repeat
- The staging backup and the page-17 deletion from staging (done 10:46 and 10:50).
- The scratch restore (done 10:47; restore again only if approved has changed).
- The candidate source verification (texts unchanged since 26 Oct). Re-extract only to get a fresh token, and compare the SHA-256.

## Previous brief: session and environment
- **This session:** Claude PID 51627, working in `/Users/arunnm/Projects/SOP`.
- **Sleep:** `caffeinate -dimsu -w 51627` (PID 28149) holds the idle-sleep and display-sleep assertions for as long as this session runs, then exits by itself.
  - No system setting was changed.
  - It does not prevent a forced sleep, a shutdown or a power cut, and it does not extend Claude's session or usage limits.
- **Another Claude session (PID 17576) is open in this project** (started 24 Oct). It is idle: its last writes were docs `13` and `14` on 25 Oct, and every file changed since is from this session. It was neither used nor stopped. **Owner:** do not use it while this work is in progress.

## Previous brief: approval boundary (superseded where the owner decided otherwise; see "Current brief: the owner's decisions")
- **Content approval:** every replacement, move or addition is approved by a human in the admin page (Extract → review → Approve). Claude prepares drafts and review packets only.
- **Migration** (`19`, "Final migration approval checklist"): needs the owner's decisions in its item 7:
  - the plan;
  - the card values;
  - the reviewers;
  - the maintenance window and the person pausing traffic.
- **New procedures** (N1–N11): the owner chooses and approves.

## Previous brief: phases
| Phase | Status | Evidence / result |
|---|---|---|
| 1. Reconnaissance and baselines | **Done** | See "Baselines" |
| 2. Remaining identification failures | **Done** (code; full suite in Phase 7) | See "Phase 2" |
| 3. Card and clarification behaviour | **Verified** (no change needed) | Frontend 67 passed; the new identification outcomes use the existing no-match, choice and card paths |
| 4. Migration sources and review packets | **Done** (prepared; nothing approved) | See "Phase 4" |
| 5. The 11 candidates | **Done** (validated; the owner chooses) | See "Phase 5" |
| 6. Ingestion and RAG workflow | **Done** | See "Phase 6" |
| 7. Comprehensive tests | **Done** | See "Phase 7"; final suite `p7_final` |
| 8. Backup and migration plan (prepare, verify) | **Done** (dry run) | See "Phase 8" |
| 9. Stop for the owner's approvals | **Reached 09:40** | Decisions listed below and in `22` §14 |
| 10–11. Migration and final validation | **Blocked on the owner** | — |

## Baselines (Phase 1, 27 Oct 02:20–02:30)
- **Git:** HEAD `3491415` ("staging"); 37 status entries, all uncommitted work preserved; no stash; nothing staged.
- **`.env`:** last modified 15 Oct 08:38:46 (not touched).
- **Approved database:** 24 pages, 122 chunks; md5 `016980eee56654079df99cddfbabaf00` / `3e45c78f7b85623ad6d9468fa9b34171`.
- **Staging database:** 26 pages, 140 chunks; md5 `8aba737fa436f74261657f7ab31eb901` / `93000b6936010307231b28f481faaa93`.
- **Test database** (`procedureassist_test`): empty.
- **Tests, run fresh:**
  - backend 244 OK;
  - frontend 67 passed;
  - type check with unused-locals and unused-parameters flags OK;
  - production build OK.
- **Evaluations:** `evidence/evaluations/p5_after/` (27 Oct 01:02–01:55). It ran on a snapshot whose `backend/`, `scripts/` and `fixtures/` files are byte-identical to the working tree (checked 02:20), on the same database checksums. It is therefore the baseline for this code, rather than a re-run of the same inputs.

  | Evaluation | Staging | Approved |
  |---|---|---|
  | Main | 75/80 | 74/80 |
  | Held-out | 23/27 | 24/27 |
  | Safety | 44/59 | 39/53 (6 skipped: page 39 not stored) |
  | Generalisation | 17/17 | 17/17 |
  | Identification failures (74) | 61/74 | 54/74 |

  Staging only: identification sets 11/14, 36/42, 32/37, 31/36; follow-ups 17/17; audit probe 42 run. Ingestion acceptance: 22/22.

## Phase 2 — remaining identification failures (done 03:40)
- **Evidence:** `evidence/investigations/p6_identification/`:
  - `trace_staging.txt` traces the real route;
  - `screen_g*_*.txt` holds the candidate rules;
  - `screen_final_*.txt` holds the adopted rules and lists every question still wrong.
- **Method:** the screen is `p5_failures/screen.py`, run with `REAL=G1235`.
  - It covers every labelled English question: 308 on staging, 306 on approved.
  - The live route is asserted equal to the screened rules on each question.
- **Root causes (traced):**
  - **Overseas wording:** the ranking prefers Register to Vote even with "abroad" in the text, so the citizen's stated residence must decide.
  - **Lower-case "i work in dubai":** the standalone question matched Overseas, but no choice rule covered it.
  - **Address change:** page 21 has its own "change of address" section (0.709 against 0.613).
  - **"idp":** lower-case words are not read as abbreviations.
  - **Marriage:** the winning section is page 17's "Inter Caste Marriage Certificate" heading.
  - **RC/DL:** below the threshold.
- **Adopted rules** (all in `backend/procedure_search.py`, plus one line in `routes.py`):
  1. **Where the citizen is.** Of two nearby sibling procedures, one for citizens abroad (its name says overseas/NRI), the message decides:
     - abroad (explicit words, or a foreign country or region in any case) → the overseas one;
     - no residence clause → the other;
     - an unknown place (a city) → scores and choice.
  2. **Extended choice:** the standalone question confidently matches another page that the whole message also finds plausible → the citizen chooses.
  3. **Abbreviations in any case:** a stored procedure's own abbreviation typed in lower case ("idp", "eps") is read in capitals.
  4. **A more specific document:** when every heading naming the asked document adds qualifiers ("Inter Caste Marriage Certificate"), the page is not matched.
- **Rejected:** spelling out RC/DL for the search. It broke six questions (IDP, VVPAT, learner's licence…), as in W11.
- **Screen results** (identification only; current → adopted):

  | | Staging | Approved |
  |---|---|---|
  | In scope correct | 196 → **213** / 235 | 187 → **204** / 233 |
  | Wrong page | 15 → 4 | 17 → 5 |
  | Missed | 8 → 6 | 13 → 12 |
  | Out-of-scope false matches | 5 → 2 | 5 → 5 (page 17 has no headings there) |
  | Questions made worse | **0** | **0** |

- **Still wrong:**
  - the 4 colloquial RC/DL misses;
  - "turned 18" ×3 and Dubai ×2 → a choice;
  - "Qatar … Lok Sabha" → no match (the pages never say "Lok Sabha");
  - "How do I get my name on the voters list?" → How to Vote;
  - "marriage registration certificate" and "PAN card fee" → false matches. The answers abstain (checked on 27 Oct for the PAN fee).
  - **Approved only, page 17 without headings:** marriage ×3 and birth certificate are matched; five certificate questions are missed.
- **Tests:** backend 251 OK (+7 new, after mutation checks that each new test fails without its rule).
- **New regression set:** `fixtures/evaluation/residence_and_documents.json` (20 cases), labelled before the screen was run.

## Phase 4 — migration sources (done 04:05; read-only)
- **Re-scrape** (`evidence/investigations/p7_migration/rescrape_27oct.txt`, `rescrape_dry.py` against staging):
  - all 15 changed pages equal their staging text exactly (no block added or removed; the same chunks: 108 in total);
  - the 11 untouched pages behave as recorded before (9 gain one label block, 2 are identical) and are not re-scraped by the plan.
- **Review packets** (`p7_migration/migration_review_packets.md`, from `migration_packets.py`):
  - the exact card for each page;
  - a summary table;
  - the 12 kept cards are identical to the approved cards today, and page 17 changes only name, summary, eligibility and steps, as planned.
- **Grounding check:** steps and eligibility checked word for word, or by word overlap, against the page.
  - Only 4 steps and 3 eligibility sentences fall below 80% overlap.
  - Page 19's two flagged steps are supported (Form 6 copies, 1950).
  - **Page 39's planned step ("Find your service in the table and pay the amount listed against it.") is not stated on the page.** The owner decides; see "Decisions".
- **Page 17 card** checked against its source: name, department (stated on the page), jurisdiction, summary and eligibility are grounded; steps 2–11 are FAQ 6 word for word.
- **Page 17, citizen questions before and after** (`p7_migration/page17_questions_*.txt`, the real API):
  - **Approved today:** birth certificate, death certificate, and applying for a community or income certificate are each answered with 9 CAN-editing steps. These are misleading answers on live data. The income and nativity document lists also mix in other certificates' items.
  - **Staging, the replacement text:** all of these abstain or get no match; the income (9 items) and nativity (5 items) document lists are correct; CAN editing gets its 10 steps.
  - **So the planned replacement fixes them.** Not executed: it needs the owner's approval. *(Later on 27 Oct the owner chose to delete page 17 instead; see the current brief above.)*

## Phase 5 — the 11 candidates (done 04:15; read-only)
- **Re-scrape** (`p8_candidates/rescrape_candidates.*`): all 11 are reachable and on official domains, and identical to their 26 Oct texts.
- **Review packets** (`p8_candidates/candidate_review_packets.md`): the model's draft cards with grounding checks and overlap with stored pages. 38 draft steps are paraphrases below 80% word overlap; a human must correct them, for example N9's steps are eligibility checks.
- **N4 (UIDAI Aadhaar enrolment) against page 35 (India Post): distinct, complementary services**, not duplicates.
  - N4 is the general enrolment procedure: documents, the head-of-family route, the Enrolment ID and the 180-day wait.
  - Page 35 is the post-office channel and the fee table.
  - Only one paragraph is shared. N4 also shares 7 Aadhaar-app FAQ paragraphs with page 18.
  - The owner decides whether to include it.
- **N1 (Instant e-PAN)** would be the first stored page for "apply for a new PAN card". Today's "no match" expectations reflect the current collection.

## Phase 6 — ingestion and RAG workflow (done 04:40)
- **Ingestion acceptance** (`scripts/evaluate_ingestion.py`, now 6 unseen official URLs: PMSBY, PCC, Krishnagiri birth registration, Instant e-PAN, NPS, TN ration card).
  - It runs on the test database in one transaction that is always rolled back; the test database is still empty afterwards.
  - **Run 1:** 35/37 checks. The e-PAN fee answer abstained.
  - **Run 2:** **37/37**.
  - The trace (`evidence/evaluations/p6_ingestion/answer_trace*.{py,json}`) shows the same question answered and verified ("free of cost"). The miss was occasional variation between model runs at temperature 0, not a rule.
- **No procedure-specific code is involved:** every page goes Extract → save → chunk and index → identify → answer through the real routes.

## Phase 7 — comprehensive tests (in progress)
- **Full suite on `snap_p6_after`** (`evidence/evaluations/p6_after/`, 03:06–03:46; both databases' checksums identical before and after):

  | Evaluation | Before (`p5_after`) | After |
  |---|---|---|
  | Main: staging / approved | 75 / 74 of 80 | **76 / 75** |
  | Held-out | 23 / 24 of 27 | 23 / 24 |
  | Safety | 44/59, 39/53 | **47/59, 40/53** |
  | Generalisation | 17/17 both | 17/17 |
  | Identification failures (74) | 61, 54 | **70, 62** |
  | Residence and documents (20) | — | 18, 16 |
  | Needs sets | 11/14, 36/42, 32/37, 31/36 | 11/14, **37/42, 33/37**, 31/36 |

  - **Case by case:** every change is an improvement, except two.
    - (a) Held-out "Which form is used to correct entries in the electoral roll?" now reaches the right page (19), but its answer abstains. Page 19's chunk starts mid-sentence ("fill form 7 … Please fill Form 8 …"), and the meaning check rejects the run-on quote. That is the chunking issue P1-3, which the owner held back. A citizen choosing page 19 from the earlier choice got the same abstention.
    - (b) **Follow-up C4** ("Can I do this at a post office?" on the Aadhaar page) went to Register to Vote. Cause: the residence rule turned a miss (all scores below 0.53) into a match. **Fixed:** the rule now chooses between the two pages only once the service clears the threshold. A unit test and a mutation check pin it. The screen is identical for all labelled questions, and the follow-ups are back to **17/17** (`p6_after/followup_scenarios_staging_after_fix.txt`).
  - Because the code changed after this run, the full suite was re-run as the final run (next item).
- **Final suite** (`evidence/evaluations/p7_final/`, code `snap_p7_final`, 08:30–09:12):
  - all 18 runs completed; both databases' checksums identical before and after;
  - **case by case equal to `p6_after`** in every answer run (0 changes), so the threshold fix changed no measured case;
  - follow-ups 17/17 with no scenario changed against before this brief; audit probe 0 of 42 changed.
  - **New set before → after** (`p7_before_new_set/`, run on `snap_p5_after`): staging 10 → 18, approved 8 → 16 of 20.
  - **Answer quality:**
    - citation failures 0; unsupported claims 0;
    - **2 incorrect claims on approved** (page 17's income and nativity lists) and **1 misleading card on staging** (page 17's old card). Both are unchanged and both are fixed by the planned replacement *(now: the planned deletion of page 17)*.
- **Final checks on the final tree:** backend 252 OK; frontend 67 passed; type check and build OK.
- **Operational tests** (`evidence/test_results/p7_ops/`; my own test instances on ports 8097–8099 and 5174, all stopped afterwards; the process on port 8000, started 23 Oct, was not touched):
  - **Smoke, input and admin checks** (`ops_normal.txt`): health and readiness OK; 24 procedures; every identify request carries a request ID; empty, over-long or unknown-field input → 422; admin without a session → 401.
  - **Concurrency** (`ops_normal.txt`):
    - 20 simultaneous identify requests: all 200, and identical to the sequential answers; median 0.3 s, maximum 2.2 s;
    - 3 simultaneous answers: all 200, in 23 s.
  - **Model outage** (`ops_model_outage.txt`; model server pointed at a closed port): readiness 503 "ollama unavailable"; liveness 200; identify and guidance each 502 with a message.
  - **Database outage during operation:** a scratch database `procedureassist_outage_test` was created, used, then dropped while the instance ran.
    - **Before the fix** (`ops_database_outage.txt`): a bare 500 with no message and no request ID.
    - **Fixed** (`backend/main.py`: a handler for SQLAlchemy `OperationalError`) → 503 "The procedure database is unavailable. Try again." with the request ID (`ops_database_outage_after_fix.txt`; unit test in `test_health.py`).
  - **Database down at startup:** the API cannot start, because `Base.metadata.create_all` runs on import. **Not changed;** it is reported as a limitation.
  - **Browser walkthrough** (automated: headless Chromium through Playwright, not a manual session; `browser_walkthrough.*`, screenshots in `browser/`): **all checks pass.**
    - passport answer with its card;
    - "I live abroad" → the overseas card with 4 claims;
    - unnamed certificate → "Which certificate…?";
    - marriage → no card;
    - follow-up fee on the open procedure;
    - Tamil-English typed question → "Searched as".
    - The Saudi question shows no card and a note: its answer abstains at generation. In 2 of 8 overseas phrasings the model drafts no claim (`p6_identification/overseas_answers_approved.txt`).
  - **Answer prompt A/B** (`p6_identification/prompt_ab*`): one added sentence about citizens' own facts fixed neither abstention and changed 5 of 16 other answers. **Rejected.**
  - **Wording fix** (`CitizenPage.tsx`): a page that found a procedure but has no verified answer now says "No approved official information answers this question yet…" instead of claiming nothing matched. Genuine no-matches keep their message.
  - **Voice** (`voice.txt`): a synthesised English (India) question was transcribed exactly by the local model; 13 s on the first request including the model load, 2.1 s warm; non-audio → 415. **Tamil speech not tested:** no Tamil voice is installed. Tamil text is covered by `tamil.json` and the walkthrough.
- **Database integrity** (`evidence/database/db_integrity.sql`, `db_integrity_27oct.txt`), on both databases:
  - no duplicate URLs, orphaned chunks or chunk-numbering gaps;
  - no missing embeddings; all 1024 dimensions;
  - cascade on delete; a unique URL constraint.

## Phase 8 — backup and migration plan (dry run done 04:55)
- **Dump:** `pg_dump -Fc procedureassist` → `/Users/arunnm/Projects/SOP-backups/procedureassist_2026-10-27_dry_run.dump`.
  - 700,813 bytes, SHA-256 `a20557ddb4903c1afb3796bbb481696bf587190e50309d2d5fdd9ec063911196`.
  - `pg_restore -l`: 35 entries (vector extension, both tables, index, foreign key).
- **Restore proven:** restored into a new scratch database `procedureassist_restorecheck`, using the plan's own sequence.
  - The copy's checksums equal the source (`016980ee…` / `3e45c78f…`), and every integrity check passes.
  - **The scratch database was then dropped**; only that name was touched (`evidence/database/restore_check_27oct.txt`).
- **This is a dry run.** The plan's step 0 (a fresh dump right before the migration) still applies.
- **Note for the owner:** a database named `procedureassist_db` exists on the server. It is not part of this project's plan and was not touched.

## Decisions required from the owner (collected)
1. The migration: `19`, checklist item 7 (plan, card values, reviewers, maintenance window and traffic person).
2. Page 39's card step (part of the card values): keep the plan's step, or use a sentence the page states. The review form requires at least one step.
3. Which of N1–N11 to add, after the migration, and their corrected cards (human review in the admin page).

## Operations that must not be repeated
- **The dry-run dump and its restore check** (Phase 8) are done. Do not restore into `procedureassist` or `procedureassist_staging`. Never drop either database.
- **No other database write has happened.** The test database is used only in rolled-back transactions.

## Database operations performed (all outside the two project databases' data)
- 27 Oct ~04:50: dry-run dump of `procedureassist` (read-only for the source).
- 27 Oct ~04:52: `createdb procedureassist_restorecheck` → `CREATE EXTENSION vector` → `pg_restore` → checks → `dropdb procedureassist_restorecheck`.
- 27 Oct ~05:30 and ~05:45: scratch database `procedureassist_outage_test` created (empty, plus the vector extension), used by a test instance, then dropped while the instance ran, twice (before and after the fix).
- `procedureassist` and `procedureassist_staging` checksums are unchanged throughout.

## Files changed in this brief
- `PROCEDUREASSIST_HANDOFF/21_AUTONOMOUS_EXECUTION_STATE.md` (new).
- `backend/procedure_search.py`: residence, countries and regions, the audience rule, `read_abbreviations`, `more_specific_document`, the extended choice, `_same_word` / `_same_service`.
- `backend/routes.py`: `read_abbreviations` before the search.
- `tests/test_identify.py`: +7 tests.
- `fixtures/evaluation/residence_and_documents.json` (new).
- `evidence/investigations/p5_failures/screen.py`, `trace.py`: new variants; the `context` and `message` arguments.
- `backend/main.py`: the database-unavailable handler (503 with a message and the request ID).
- `tests/test_health.py`: +1 test.
- `frontend/src/CitizenPage.tsx` (+ test): the honest note for a found procedure without an answer.
- `scripts/evaluate_ingestion.py`: +3 unseen URLs.

## Database operations performed in this brief
- None. All database access so far is read-only.

## Known failures and unresolved issues (from `20`, 27 Oct)
- Overseas wording the ranking does not separate: Saudi Arabia, Singapore, lower-case Dubai.
- The electoral-roll address change goes to the Overseas page.
- Lower-case abbreviations ("idp").
- Marriage certificate matched to page 17 at identification (the answer abstains; no card).
- Four colloquial or RC/DL misses.
- **Approved data only:** page 17 answers "birth certificate in Tamil Nadu" with the CAN-editing steps. The planned page 17 replacement was meant to fix this; *the owner later chose deletion (current brief)*.
