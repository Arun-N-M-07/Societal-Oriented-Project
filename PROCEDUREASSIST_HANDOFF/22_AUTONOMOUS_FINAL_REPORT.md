# 22 — Final reports

## Final Autonomous Execution, Procedure Approval, Database Correction & Reliability Verification (27–28 Oct 2026)
**State.** Complete up to the owner-approval boundary (28 Oct 10:45 IST).
- **Running log:** `21`. **Roadmap:** `10`. **Migration checklist:** `19`, "Final migration approval checklist".
- **Not done, on purpose:**
  - no production migration;
  - page 17 is still in the approved database;
  - nothing committed or pushed;
  - `.env` untouched.

### A. Code changes
| File | Change | Why |
|---|---|---|
| `backend/procedure_search.py` | **1 line**: `acronym_names` ignores one-letter name pieces | The "e" of "e-PAN" made any "e-…" word name Instant e-PAN: a measured misleading card (`11` #56) |
| `tests/test_identify.py` | +3 lines: 2 assertions and a comment | Pins that fix; the test failed before it |
| `scripts/evaluate_answers.py` (+7 net), `scripts/evaluate_needs.py` (+1 net) | A page fragment must not be followed by a letter or digit; `unless` skip key | `psp/Apply` (passport) vs `psp/ApplyPCC`; labels for the deleted page 17 |
| `fixtures/evaluation/*.json` | Labels for the changed collection, written before the runs (details below the table) | `10` P1.1–P1.2, `11` #51–52 |
| Evidence tooling (not application code) | `validate_migration.py` and its self-test, `migration_packets.py` (page 17 deleted; page 39 step); new `p9_final/admin_workflow.py`, `card_safety.py` | Migration preparation; delegated approvals through the real routes |

- **The fixture label changes:**
  - `passportindia`→`psp/Apply`; `uidai`→`updating-data-on-aadhaar`;
  - `requires`/`unless` for page 17;
  - 4 after-deletion cases; 9 candidate cases; 9 relabels.
- **Net lines of application code: 0.** No new dependency, module, service, layer or threshold change.
- **Existing behaviour preserved:** the identification rules, the human review and approval, the card rule. Re-extract was not reintroduced.

### B. Procedure review and approval (delegated by the owner; `evidence/investigations/p9_final/candidate_review_27oct.md`)
| Candidate | Official source (verified 27 Oct; text unchanged since 26 Oct) | Corrections | Final metadata | Tests | Decision |
|---|---|---|---|---|---|
| **N3** Police Clearance Certificate | `passportindia.gov.in/psp/ApplyPCC` | Form-section headings folded into one step; jurisdiction India; the 90-day revisit rule and SMS proof added; eligibility left empty (the page states none) | "Apply for Police Clearance Certificate (PCC)", Passport Seva, India; 10 steps | Production copy and both databases; PCC questions answered; side effects safe (passport-fee choice; lower-case "idp" no match) | **APPROVED** (approved id 39, staging id 41) |
| **N4** Aadhaar Enrolment | `uidai.gov.in/en/aadhaar-enrolment` (updated 3 Jul 2026) | The head-of-family route is no longer presented as universal; "enrol only once" and the 180-day wait added | "Aadhaar Enrolment", UIDAI, India; 6 steps | No regression found; distinct from pages 18 and 35 | **APPROVED** (40 / 42) |
| **N8** Registration of Births and Deaths | `krishnagiri.nic.in/scheme/civil-registration-system` (statewide TN rules on a district site; undated) | RCH ID attributed to the page, not universal; Form 4 / 4A; the page's conflicting late-registration sentences reported as written | Jurisdiction Tamil Nadu, department "Krishnagiri District Administration (Civil Registration System)"; 6 steps | Birth/death questions now answered correctly. 7 TN certificate questions are falsely identified as N8; all abstain with no card | **APPROVED** (41 / 43) |
| **N1** Instant e-PAN | `incometax.gov.in/…/instant-e-pan` | Typo, exclusions and sections fixed; 18 steps merged into 8 | — | A lost/duplicate PAN question can reach the verified answer "you can apply for an Instant e-PAN" that the page contradicts | **DEFERRED** (`11` #57) |
| **N10** New ration card | `consumer.tn.gov.in/eligibility_ration.htm` | — | — | The page's route dates from 2008; no readable current official page | **DEFERRED** |

N2, N5, N6, N7, N9 and N11 were not added (the owner's deferral).

### C. Database migration (prepared; **NOT executed**)
- **Scope:**
  - **delete** page 17;
  - **replace** 18, 19, 20, 27, 35, 36, 37, 38;
  - **move** 16, 31, 32, 33;
  - **add** the Vehicle Registration fee table and APY (PFRDA);
  - **leave 11 untouched.**
- **Result after it:** **28 pages / 146 chunks.** That is staging now, and it includes N3, N4 and N8, which are already in both databases.
- **Page 17 deletion:**
  - tested on a production copy through the real route, rolled back (only its 4 chunks go; every other row unchanged);
  - rehearsed on staging.
- **Card field review:** corrections proposed for 18, 20, 33 (assessment year attributed), 36, 37 and 38 (**owner approval**); 19, 27 and 35 unchanged; page 39's step as the owner decided.
- **Backups:**
  - **production dump** 27 Oct 10:46: SHA-256 `20b54b9e…`; restored into a scratch database with equal checksums;
  - **staging dump** 10:46: SHA-256 `9616f56c…`; restored with equal checksums, then the restore database was dropped.
  - **A fresh production backup and restore check are still required immediately before the migration.**
- **Execution status: not run.** It needs the owner's approval.

**The migration approval packet (owner's brief §11, 18 items):**

| # | Item | Where |
|---|---|---|
| 1 | Revised scope | This section; `19` item 1 |
| 2 | Page 17 deletion details | `19` item 1 (row 7), item 4 step 4a; `07` "Current state"; `p9_final/page17_deletion_test_scratch.txt` |
| 3 | Eight replacements | `19` item 1; packets `p7_migration/migration_review_packets.md` |
| 4 | Four URL moves | `19` item 1 |
| 5 | Two additions | `19` items 1–2 |
| 6 | Eleven untouched records | `19` item 1 |
| 7 | Five candidate outcomes | Section B above |
| 8 | Expected counts | 28 pages / 146 chunks (staging now) |
| 9 | Record-level changes | `19` item 1 table; `p9_final/validate_approved_after_candidates.txt` lists every difference today |
| 10 | Fresh backup instructions | `19` item 5 |
| 11 | Verified restoration | `19` item 5. Both 27 Oct dumps were restored with equal checksums (`evidence/database/restore_check_staging_27oct.txt`, `21`) |
| 12 | Integrity validation | `validate_migration.py --embeddings` (expect 0 failures) and `evidence/database/db_checksums.sql` |
| 13 | Evaluation commands | `09`; `evidence/other/scripts/run_suite.sh` with the four extra fixtures, compared with `p9_final` |
| 14 | Maintenance window | `19` item 4: **the owner fills it in** |
| 15 | Traffic pause and resume | `19` item 4: **the owner names the people** |
| 16 | Stop conditions | `19` item 5 ("If any operation or validation fails") |
| 17 | Restoration procedure | `19` item 5, steps 1–6 (only on the owner's decision) |
| 18 | Risks and unresolved limitations | Section D above; `10` |

### D. Evaluation (`evidence/evaluations/p9_final/`, code `snap_p9_fix`; compared with `p9_baseline/`)
| Metric | Staging, baseline → final | Approved, baseline → final |
|---|---|---|
| Answer sets as expected | 237/259 → 237/270 (more cases run) | 229/264 → 230/275 |
| Correct answers (+ partial) | 148 (+20) → 156 (+21) | 147 (+21) → 153 (+22) |
| Correct identifications | 245 → 245 | 239 → 239 |
| Confident wrong page (false positives) | 1 → 8 | 5 → 11 |
| Missed (false negatives) | 6 → 7 | 12 → 12 |
| Clarifications (asked) | 7 → 10 | 8 → 12 |
| Appropriate abstention / no match | 60 → 51 | 52 → 47 |
| Unsupported answers | 0 → 0 | 0 → 0 |
| Incorrect answers (forbidden claims) | 0 → 0 | 2 → 1 (page 17's income list) |
| Citation failures | 0 → 0 | 0 → 0 |
| Misleading cards | 0 → 0 | 0 → 0 |
| Follow-ups | 17/17 | — |
| Audit probe | 0 of 42 changed | — |

- **Unit and build checks:** backend 252 OK; frontend 67 passed; strict type check OK; production build OK.
- **Ingestion acceptance:** 6 unseen official URLs through Extract → approve → identify → answer, on the test database (rolled back; still empty): **38 of 40 checks pass, in both runs** (`p9_final/ingestion_acceptance*.txt`). The 2 failures are one case, "Is there any fee for an instant e-PAN?": it is identified correctly, but the model writes the FAQ question as the claim while quoting "No. The service is free of cost.", so the negation rule rejects it. That is a safe abstention from model output, not from code (`p9_final/epan_fee_trace.txt`); on 27 Oct the same case failed once and passed once.
- **Every new false positive was traced:** no card and no claim (the citizen sees "No approved official information answers this question yet…").
- **The browser walkthrough was automated** (27 Oct); no manual walkthrough this brief. **Tamil voice is untested.**
- **Limitations (`10`):**
  - abbreviations need the page in the top 3;
  - no document-type model;
  - P1-3, 2 of 8 overseas phrasings, the 4 RC/DL misses;
  - N1's path.

### E. Database integrity
- **Approved:** 27 / 134 (`750d4dc2…` / `e7fee548…`). The original 24 pages and their chunks are **byte-identical**; the only writes were 3 delegated approvals.
- **Staging:** 28 / 146 (`c442a59c…` / `290cf496…`). Writes: the page 17 deletion and the 3 approvals; earlier rows byte-identical.
- **All databases:** 0 orphans, 1024-dimension embeddings, no index gaps, no duplicate URLs.
- **Validator:** the new pages pass against staging. Approved differs only by the planned migration.
- **`procedureassist_scratch`:** a test copy with N1. It may be dropped.

### F. Operational state
- **Port 8000:** restarted 28 Oct 10:31.
  - The old PID 75965 (23 Oct code) was stopped. The new PID 89049 runs the same command and is detached.
  - Health and readiness are OK. The responses carry `named` and an `X-Request-ID`, so it is the current code, and N8 answers a birth-certificate question.
  - No other process was touched. The other Claude session (PID 17576) stayed idle.
- **Manual vs automated:** the browser verification was automated only. Voice was tested on a synthetic English voice; **Tamil speech is untested.**

### G. Safety confirmation
- `.env` untouched (modified 15 Oct).
- No commits, no pushes, no destructive Git operations.
- **Approved-database writes:** only the 3 delegated approvals, through the admin routes. No unapproved production change.
- No unrelated record deleted or re-embedded.
- No re-scrape or re-extract feature reintroduced.
- No threshold lowered; no LLM identification layer; no page-specific rule.

### H. Owner decisions remaining
1. **Approve the production migration:**
   - the page 17 deletion;
   - the 8 replacements, 4 moves and 2 additions;
   - the maintenance window (start, end) and who pauses traffic, resumes it and verifies the result (`19`, item 7).
2. **Approve or reject the proposed card corrections** for 18, 20, 33, 36, 37 and 38 (`p9_final/replacement_field_review.md`).
3. **Optional:**
   - N1 after a general fix (`11` #57);
   - N10 with a current official source;
   - commit the uncommitted work (43+ entries, including the untracked handoff folder).

---

## Earlier report: autonomous reliability, database correction and generalisation (27 Oct 2026)

> **Superseded in part (27 Oct 2026, later brief "Final Autonomous Execution…").**
> - Page 17 is now **deleted, not replaced**. Statements below about its replacement or rename are historical.
> - Page 39's step was decided by the owner.
> - N1, N3, N4, N8 and N10 were delegated to Claude for review and approval; N2, N5, N6, N7, N9 and N11 were deferred by the owner.
>
> Current state: `21` (current brief at the top) and `00`.

**Brief:** "Autonomous Final Reliability, Database Correction & Generalisation".

**State:** Phases 1–8 done and measured. Stopped at the approval boundary (Phase 9). Phases 10–11 (the migration and its validation) wait for the owner. The running log and evidence index are in `21_AUTONOMOUS_EXECUTION_STATE.md`.

**What was not done, on purpose:**
- no procedure content approved;
- no database migrated;
- nothing committed or pushed;
- `.env` untouched.

## 1. Remaining identification failures and their resolutions
| Failure (from `20`) | Traced cause | Resolution | Result |
|---|---|---|---|
| Saudi Arabia, Singapore → Register to Vote | The ranking prefers Register to Vote even with "abroad" stated (measured); the need phrase drops the residence | **Where the citizen is:** of two sibling procedures, one for citizens abroad, the message decides. Abroad (a foreign country or region in any case, NRI, outside India) → overseas; no residence clause → general; an unknown place → scores and choice. Only once the service clears the threshold. | Both → Overseas Voter Registration |
| Lower-case "i work in dubai" | The standalone question matched Overseas, the message leaned to Register to Vote, and no choice rule covered it | **Extended choice:** the standalone question confidently matches another page that the whole message also finds plausible → the citizen chooses | A choice (Register to Vote or Overseas); "Dubai" is a city the code cannot place |
| Address change → Overseas page | Page 21 has its own change-of-address section (0.709 against 0.613) | The residence rule's "no residence clause → general" direction | → Register to Vote (Form 8) |
| Lower-case "idp" | Lower-case words were never read as abbreviations | **Abbreviations in any case:** a stored procedure's own abbreviation typed in lower case is read in capitals; "lpa" (salary) is protected | → International Driving Permit (both databases) |
| Marriage certificate (internal match) | The winning section is page 17's heading "documents required for applying Inter Caste Marriage Certificate", a more specific certificate | **A more specific document:** when every heading naming the asked document adds qualifiers the question lacks, the page is not matched | No match on staging (= the replacement text). Approved page 17 has no headings, so it is fixed there by the planned replacement |
| Four colloquial RC/DL questions | The right page is ranked first but below 0.53 | Not fixed. Spelling out RC/DL broke six other questions (IDP, VVPAT, learner's licence…); the threshold stays | They abstain |

## 2. Root causes and code changes
- **`backend/procedure_search.py`** (+107 / −14; 350 → 443 lines, about 17 of them the country and region reference list):
  - `residence`, `ABROAD`, `FOR_CITIZENS_ABROAD`, `COUNTRIES` and the sibling-audience rule in `_decide`;
  - `read_abbreviations`;
  - `more_specific_document` (`NAMED_DOCUMENT`);
  - the extended choice rule in `identify`;
  - `_same_word` and `_same_service`, shared word comparisons;
  - the `message` argument of `_decide`.
- **`backend/routes.py`** (+3 / −1): lower-case abbreviations are read before the search.
- **`backend/main.py`** (+9): a database that cannot be reached returns 503 with a message and the request ID, not a bare 500. Found by the outage test.
- **`frontend/src/CitizenPage.tsx`**: a found procedure without a verified answer says "No approved official information answers this question yet…", not "we don't have an approved procedure".
- **Tests:**
  - backend 244 → 252 (identification +7, health +1);
  - frontend 67 (one expectation updated for the new wording).
- **One bug caught by the follow-up scenarios, before the final run:** the first version of the residence rule turned a miss into a match ("Can I do this at a post office?" → Register to Vote at 0.497). It was fixed so that the rule only chooses between pages once the service clears the threshold. It is pinned by a unit test and a mutation check.

## 3. Database corrections completed
**None.** Every correction is procedure content, which only a human approves in the admin page. The migration also needs the owner's decisions (§14).

What was prepared and verified instead:
- **Re-scrape:** all 15 changed pages equal their staging text exactly.
- **Review packets:** for all 15 pages.
- **Page 17 before and after:** measured with citizen questions (§4).
- **Backup:** a dump, proven restorable (§7).

## 4. Procedures replaced, moved, added and retained (the plan in `19`; not executed)
- **Add (2):**
  - Vehicle Registration Fees and User Charges;
  - Atal Pension Yojana (PFRDA scheme details).
- **Move (4):** 16 Filing of ITR-2; 31 Link PAN with Aadhaar; 32 Register on the e-Filing Portal; 33 File ITR-1 (Sahaj) Online.
- **Replace (9):** 17 (renamed "e-Sevai FAQ: CAN and certificate documents"), 18, 19, 20, 27, 35, 36, 37, 38. *(Revised 27 Oct: 17 is deleted, so 8 replacements remain.)*
- **Retain untouched (11):** 15, 21, 22, 23, 24, 25, 26, 28, 29, 30, 34.
- **Page 17, citizen questions** (`evidence/investigations/p7_migration/page17_questions_*.txt`):
  - **Today:** birth certificate, death certificate, and applying for a community or income certificate are answered with the **9 CAN-editing steps** (misleading). The income and nativity document lists mix in other certificates.
  - **With the replacement text:** these abstain or get no match; the income list (9 items) and nativity list (5 items) are correct; CAN editing gets its steps.

## 5. Official URLs
- **Planned additions:**
  - `https://parivahan.gov.in/en/content/fees-and-user-charges`
  - `https://www.pfrda.org.in/schemes/atal-pension-yojana-apy`
- **Candidates N1–N11** (all reachable, official and identical to 26 Oct; drafts with grounding checks in `evidence/investigations/p8_candidates/candidate_review_packets.md`): see `20`, "Phase 2". The owner chooses which to add.

## 6. Final procedure and chunk counts
**Unchanged:**
- **Approved:** 24 pages, 122 chunks (`016980ee…` / `3e45c78f…`).
- **Staging:** 26 / 140 (`8aba737f…` / `93000b69…`).
- **After the planned migration:** 26 / 140.

## 7. Database integrity
Both databases pass (`evidence/database/db_integrity_27oct.txt`):
- no duplicate URLs, orphaned chunks, missing embeddings or numbering gaps;
- 1024-dimension embeddings;
- cascade on delete; a unique URL.

**Backup dry run:**
- `procedureassist_2026-10-27_dry_run.dump`, SHA-256 `a20557dd…`;
- restored into a scratch database: identical checksums, integrity passes; then dropped.

**Checksums:** identical before and after every run in this brief.

## 8. Test results
Run on the final working tree (27 Oct, after the last change):
- **Backend:** **252 OK** (244 at the start; identification +7, health +1). Each new rule's test was mutation-checked: it fails when the rule is disabled.
- **Frontend:** **67 passed**.
- **Type check** with unused-locals and unused-parameters flags: OK.
- **Production build:** OK.
- **Full evaluation suite** on a frozen snapshot of this code (`evidence/evaluations/p7_final/`, 08:30–09:12): all 18 runs completed; both databases' checksums identical before and after.

## 9. Before-and-after evaluation metrics
Before = the code at the start of this brief (`p5_after`; the new set on `snap_p5_after`). After = `p7_final`.

| Evaluation | Staging: before → after | Approved: before → after |
|---|---|---|
| Main (80) | 75 → **76** | 74 → **75** |
| Held-out (27) | 23 → 23 | 24 → 24 |
| Safety (59; 53 judged on approved) | 44 → **47** | 39 → **40** |
| Generalisation (17) | 17 → 17 | 17 → 17 |
| Identification failures (74) | 61 → **70** | 54 → **62** |
| Residence and documents (20, new) | 10 → **18** | 8 → **16** |
| Identification sets (staging): multi-need, population, demo, Tamil | 11/14, 36/42, 32/37, 31/36 → 11/14, **37/42, 33/37**, 31/36 | — |
| Follow-up scenarios (17) | 17 → 17 (no scenario changed) | — |
| Audit probe (42) | 0 of 42 changed | — |

**Case by case against before** (`cmp_eval.py`): every change is an improvement except one.
- **Improved:**
  - "I live abroad. How do I register to vote?" is now answered from the overseas page (main and safety, both databases);
  - the two marriage-certificate questions get no match (safety on staging; two identification sets);
  - the overseas, address-change, "idp" and PAN cases in the regression sets.
- **The one exception:** held-out "Which form is used to correct entries in the electoral roll?" now reaches the right page (Register to Vote) but its answer abstains, because the page's chunk starts mid-sentence (P1-3). Before, the citizen was asked to choose, and choosing that page gave the same abstention.

**Answer quality in the final run** (all answer runs; the evaluator checks every claim's quote against the passage of the page it cites):

| Kind | Staging | Approved | Notes |
|---|---|---|---|
| Citation failures | 0 | 0 | |
| Unsupported claims (answered although the page does not state it) | 0 | 0 | |
| **Incorrect claims** (a forbidden claim) | 0 | **2** | Approved page 17: the income and nativity document lists mix in other certificates' items. Unchanged by this brief; staging (the replacement text) answers both correctly |
| **Misleading card** | **1** | 0 | Staging: a correct income-certificate answer under page 17's old card "REV-101 Community Certificate". The planned card values rename it |
| Missed answers (correct page, no verified claim) | 7 | 6 | Main 1/2, held-out 2/2, safety 4/2 |
| Incomplete answers | 2 | 2 | Safety set |

No incorrect claim, unsupported claim or citation failure was introduced by this brief: all of the above are unchanged cases, or the one case explained above.

## 10. False positives and false negatives (identification, every labelled English question; `screen_final_*.txt`)
| | Staging: before → after | Approved: before → after |
|---|---|---|
| Correct procedure matches (in scope: 235 / 233) | 196 → **213** | 187 → **204** |
| Wrong page in scope (a kind of false positive) | 15 → **4** | 17 → **5** |
| False negatives (missed, in scope) | 8 → **6** | 13 → **12** |
| Asked to choose (in scope; includes the right page) | 16 → 12 | 16 → 12 |
| Correct abstentions (out of scope: 62) | 55 → **59** | 54 → **55** |
| False positives (out of scope, matched) | 5 → **2** | 5 → 5 |
| Correct clarifications (no document named: 6) | 6 → 6 | 6 → 6 |
| Questions made worse | — | **0 / 0** |

- **The 5 approved out-of-scope false positives** are page 17 without headings: marriage ×3, birth certificate and marriage registration. The planned page 17 replacement removed them *(now: the deletion of page 17 does)* (they are correct on staging).
- **Unsupported and incorrect answers:** see §9. The main set's only failures are clarifications and missed answers, no forbidden claim.

## 11. Ingestion results for previously unseen URLs
`scripts/evaluate_ingestion.py` takes 6 unseen official pages through the real routes on the test database (rolled back): PMSBY, Police Clearance Certificate, Krishnagiri birth registration, Instant e-PAN, NPS, TN new ration card.
- Each went Extract → save → chunk and index (1024-dimension embeddings) → identify → an answer citing only its own page. **No procedure-specific code.**
- **Run 1:** 35/37 checks; the e-PAN fee answer abstained once.
- **Run 2:** **37/37**.
- A trace shows the same question answered and verified ("free of cost"). The miss was variation between model runs at temperature 0.

## 12. Operational test results (`evidence/test_results/p7_ops/`)
- **Smoke, input and admin:** all pass; every request carries an ID.
- **Concurrency:**
  - 20 simultaneous identify requests: all 200, identical to sequential; median 0.3 s, maximum 2.2 s;
  - 3 simultaneous answers: all 200, 23 s.
- **Model outage:** readiness 503; identify and guidance 502 with a message.
- **Database outage during operation:** fixed from a bare 500 to a 503 with a message and the request ID. **The database down at startup is not handled:** the API does not start (limitation).
- **Browser walkthrough** (automated with Playwright; not manual): all checks pass. Screenshots are in `p7_ops/browser/`.
- **Voice:** a synthesised English (India) question was transcribed exactly by the local model; 13 s cold, 2.1 s warm. **Tamil speech was not tested** (no Tamil voice installed); Tamil text is covered.
- **Not run:** a manual session by a person; load beyond 20 simultaneous requests; a real production deployment.

## 13. Remaining limitations
- **Approved data until the migration:** page 17 answers birth and death certificate and certificate-application questions with CAN-editing steps, and mixes certificate document lists. **This is the most important open item, and the replacement fixes it (§4).**
- **The answer model declines some overseas questions** (2 of 8 phrasings; the model drafts no claim). The citizen then gets the honest note. A prompt change was tested and rejected (§2).
- **Cities it cannot place** ("Dubai", "Chennai") leave the choice to the citizen; "Lok Sabha" (named on no page) blocks a match.
- **Chunks split mid-sentence (P1-3, held back by the owner):** page 19's "Form 8" answer abstains.
- **Still missed:** the four colloquial RC/DL questions; "turned 18" gets a choice; "How do I get my name on the voters list?" goes to How to Vote.
- **The backend does not start without the database.**
- **The process on port 8000** (a backend started 23 Oct) still runs the code of that day until it is restarted.

## 14. Decisions still requiring the owner
1. **The migration** (`19`, checklist item 7): approve the plan, the card values (pages 17, 39, 40; *since revised: 17 deleted, 39's step decided*) and the reviewers; fill in the maintenance window and the person pausing traffic.
2. **Page 39's planned step** ("Find your service in the table and pay the amount listed against it.") is not stated on the page. Keep it, or use a sentence the page states. The review form requires at least one step. *(Decided 27 Oct: "Refer to the fee table to identify the applicable fee for the relevant vehicle-related service.")*
3. **Which of N1–N11 to add after the migration**, each approved by a human in the admin page *(decided 27 Oct: N1, N3, N4, N8, N10 delegated to Claude; the other six deferred)*:
   - N4 (UIDAI enrolment) is complementary to page 35, not a duplicate;
   - N1 (Instant e-PAN) would answer "apply for a new PAN card".
4. **Optional:** whether to drop the empty `procedureassist_db` database (left untouched) and the dry-run dump, once the real step-0 backup exists.

## 15. Git
- HEAD `3491415` ("staging"), unchanged.
- **38 status entries:** the 37 at the start of the brief plus `fixtures/evaluation/residence_and_documents.json`. Every earlier uncommitted change is preserved.
- **Nothing staged, no stash. No commit and no push in this brief.**

## 16. `.env`
Last modified 15 Oct 2026 08:38:46. Not modified in this brief.

## 17. Autonomous execution checkpoints
- `21` was updated after each phase (Phase 1 02:30; Phase 2 03:40; Phases 3–5 04:15; Phases 6–8 05:00 and 06:00; final).
- `caffeinate -dimsu -w 51627` kept the Mac awake for this session only. It changed no system setting, and does not survive a shutdown or a session limit.
- Another Claude session (PID 17576) is open in this project. It was idle throughout, and was neither used nor stopped.
