# 10 — Pending work: the prioritised roadmap (27 Oct 2026, evening)

- **Order:** work top-down. Each task says why it is needed, where to work, what it depends on, the expected result, how to validate it, and whether the owner must approve.
- **Owner approval:** "Owner approval: YES" means stop and ask for the exact operation. Everything else is permitted (`00` §8).
- **State:** the current state is in `00` §5 and `21`.

## P1 — Immediate continuation (make the measurements honest for the changed collection)

### P1.1 Evaluation labels for the deleted page 17 — COMPLETE (27 Oct 21:31; plan below as implemented; the needs-set option taken: relabel `[null]` with a note)
- **Why.** Staging no longer has page 17; the approved database still does until the migration.
  - **15 answer-set cases expect `tnesevai`:**
    - `identification_failures.json`, 8: inter caste marriage, widow, caste, nativity, OBC and solvency certificates, nativity and income in TN;
    - `residence_and_documents.json`, 3;
    - `safety.json`, 4: TN income, community and nativity document lists, CAN editing.
  - **2 needs-set cases expect it too:** `demo_services.json` and `multi_need.json`, "How can I edit my CAN details…".
  - **Effect today:** on staging these report failures that are not real, and **no case tests the behaviour after the deletion** (owner's brief §3.4).
- **Where:** `fixtures/evaluation/*.json`.
  - `scripts/evaluate_answers.py` already supports `"requires": [fragment]` (skip unless stored) and, since 27 Oct, `"unless": [fragment]` (skip while stored). Neither has been exercised by a run yet.
  - `scripts/evaluate_needs.py` has neither.
- **Plan, decided 27 Oct before any run:**
  1. Add `"requires": ["tnesevai"]` to the 15 cases.
  2. Add their after-deletion counterparts with `"unless": ["tnesevai"]`, labelled from the stored pages. These expect no match (`[null]`, `"answer": null`), because no stored page covers these certificates or CAN editing:
     - TN income, community and nativity certificate documents;
     - "How can I edit my CAN details on the TN e-Sevai portal?";
     - inter caste marriage, widow and caste certificates.

     The existing `[null]` marriage, legal-heir and other-state cases stay as they are.
  3. For the 2 needs cases: the needs sets run on staging only (`run_suite.sh`). Relabel them `[null]` with a `"note"`, or give `evaluate_needs.py` the same two keys (about 3 lines). **Prefer the smaller change.**
- **Expected result:**
  - on approved, the old cases run and the new ones are skipped;
  - on staging, the reverse;
  - no other case changes.
- **Validation:**
  - run the affected fixtures on both databases;
  - the number of `SKIP` lines must equal the plan;
  - compare every other case with `evidence/evaluations/p7_final/`.
- **Rules:** labels change only because the owner changed the collection. Write them before running, and record each change and its reason in `21` and `05`.
- **Owner approval:** no.

### P1.2 Labels for the cases the delegated candidates change — COMPLETE (27 Oct 21:31, before any candidate was stored)
- **Why.** Once N1, N3, N4 and N8 are stored, some "no page answers this" expectations become wrong, and some correct cases may be taken by a new page.
  - The URL fragments are already unambiguous: `psp/Apply` (passport) vs `psp/ApplyPCC` (N3), and `updating-data-on-aadhaar` vs `aadhaar-enrolment`.
  - Evaluator boundary matching was added 27 Oct; see `21`.
- **Plan, decided 27 Oct before any run.** Relabel, adding `"requires": [fragment]`, so a database without the candidate skips the case:

  | Fixture | Message | Old | New |
  |---|---|---|---|
  | `answers.json`, `safety.json` | How do I get a birth certificate? | `[null]` | `["krishnagiri"]` |
  | `identification_failures.json` | How do I get a death certificate? / How do I get a birth certificate in Tamil Nadu? | `[null]` | `["krishnagiri"]` |
  | `generalisation.json` | How do I register the birth of my child? | `[null]` | `["krishnagiri"]` |
  | `generalisation.json` | How do I apply for a new PAN card? | `[null]` | `["instant-e-pan"]` |
  | `identification_failures.json` | What is the fee to apply for a PAN card? | `[null]` | `["instant-e-pan"]`. Re-judge after testing: N1 says the e-PAN is "free of cost"; the physical card fee is not stored |

  - **Keep `[null]`:**
    - PAN changes, corrections, duplicates and reprints (N1 is only for a person without a PAN);
    - "Can NRIs apply for a PAN card?";
    - legal heir and marriage;
    - police complaints (PCC is not a complaint);
    - ration cards (N10 deferred).
  - **Keep** "Is Aadhaar enrolment free at the post office?" → page 35, and every Aadhaar-update case → page 18.
- **Add, in `generalisation.json`** ("general probes"; unseen official pages fit it; no new file), with `requires`:
  - **N3:**
    - "How do I apply for a police clearance certificate?";
    - "I need a PCC for a job abroad. How do I get one?";
    - "Do I need an appointment to get a police clearance certificate?"
  - **N4:**
    - "How do I enrol for Aadhaar for the first time?";
    - "My child has no documents. Can she still get Aadhaar?" (evidence: Head of Family);
    - "How long does it take to get Aadhaar after enrolment?" (180 days)
  - **N8:**
    - "Within how many days must a birth be registered in Tamil Nadu?" (21 days);
    - "Which form is needed to register a death that happened at home?" (Form 4A);
    - "Can I change my child's name after registering the birth?" (gazette notification)
  - **N1:**
    - "How can I get a PAN instantly using my Aadhaar?";
    - "Can a minor apply for instant e-PAN?";
    - "How do I download my e-PAN?"

  Each `evidence` pattern must be text the page states (the evaluator warns `UNVERIFIABLE` otherwise).
- **Expected result:** the cases skip until the candidate is stored, then measure it.
- **Validation:** see P2.1.
- **Owner approval:** no.

### P1.3 Baseline with the new labels — COMPLETE (27 Oct 21:34–22:25, `evidence/evaluations/p9_baseline/`, snapshot `snap_p9_labels`)
- **Result.** Case by case against `p7_final`, the only changes are the planned skips, the new cases, and two improvements from the page 17 deletion on staging:
  - "marriage registration certificate": the false match to page 17 → no match;
  - "Community Certificate and a driving licence renewal": page 17 → no match + renewal.
- **The 4 after-deletion cases** (income, community and nativity documents; CAN editing) give no match on staging: no CAN steps, no card.
- **Follow-ups 17/17; audit probe 0 of 42 changed;** both databases unchanged by the run.
- **Why:** the "before" numbers for the candidates, and the first measurement of the 25-page staging collection.
- **How:** run the suite (`09`) on staging and on `procedureassist_scratch` (a copy of approved), with the labels from P1.1–P1.2 and a fresh code snapshot.
  - `run_suite.sh` takes "approved" from `.env`.
  - For the scratch copy, run `evaluate_answers.py` with `DATABASE_URL` set to the scratch database, as `09` shows.
- **Expected result:** staging equals `p7_final` staging except for the planned skips and new cases. On staging, each page-17 question gets no match or a clarification, never a CAN step.
- **Owner approval:** no.

## P2 — Delegated candidate approval (N1, N3, N4, N8; N10 deferred)
**Reference:** `evidence/investigations/p9_final/candidate_review_27oct.md` (reviews, card files, exact commands).

### P2.1 Test on the production copy — COMPLETE (27 Oct 22:27 – 28 Oct 09:31; results and every trace in `evidence/investigations/p9_final/candidate_review_27oct.md`, "Outcome after testing")
1. Approve N1, N3, N4 and N8 into `procedureassist_scratch` with `admin_workflow.py`: `extract`, then `approve` with the card files.
2. Run the suite there and compare it case by case with the P1.3 scratch baseline.
- **Pre-approval checks** (found in the code review):
  - **N1:** the single letter "e" of "e-PAN" in `procedure_search.acronym_names`. "How do I update my email on my PAN card?" must not match N1.
  - **N4:** "Aadhaar Enrolment" is inside page 35's name, so `named_by_the_others` may send post-office questions to N4. "Is Aadhaar enrolment free at the post office?" must stay page 35.
  - **N8:** the page never names Krishnagiri, so "…in Krishnagiri" questions fail the name check. Record it; it is not a blocker.
- **Expected result:** the candidates answer their own questions with no new false match. Any harm is recorded with its cause.
- **Owner approval:** no.

### P2.2 Decide per candidate — COMPLETE (28 Oct 09:31)
- **N3, N4, N8:** APPROVED.
- **N1:** DEFERRED. A lost/duplicate PAN question can reach a verified answer that the page contradicts (`11` #57).
- **N10:** DEFERRED (outdated route).
- **The code fix needed:** `acronym_names` one-letter pieces (`11` #56).

Original plan:
- **Approve** only if every §5.4 check of the owner's brief passes.
- **Otherwise:**
  - record why;
  - correct the card only from the page;
  - re-test;
  - or defer.
- **If a generic code fix is needed** (e.g. one-letter words in `acronym_names`): make it the smallest change, with a positive and a negative unit test and a mutation check. Then re-run the identification screen on every labelled question (`20`) and the suite.
- **Owner approval:** no for the four candidates. A code change is ordinary work: tests, no approval.

### P2.3 Approve into staging, then production — COMPLETE for N3, N4, N8 (28 Oct 09:33–09:34)
- **Approved database:** ids 39–41, 27 pages / 134 chunks.
- **Staging:** ids 41–43, 28 / 146.
- **Unrelated rows** byte-identical in both.
- **Validator:** the new pages pass against staging.
- **Evidence:** `p9_final/candidates_approval_staging_production.txt`.

Original plan:
- **Commands:** the same `approve` into `procedureassist_staging`, then `procedureassist`.
  - Extract again if the 2-hour token has expired, and compare the text's SHA-256 with the review.
  - `admin_workflow.py` allows only the five delegated URLs in `procedureassist`.
- **Before production:** take a `pg_dump` (good practice, although adding is not destructive).
- **After each save, record:**
  - the `approve` output (chunks equal `chunk_text`; vectors valid);
  - the database checksums;
  - the new counts.
- **Expected result:** approved 28 pages / about 145 chunks; staging 29 / about 157 (estimates).
- **Owner approval:** **no (delegated).** Do not approve any other page there.

### P2.4 Measure after approval — COMPLETE (28 Oct 09:35–10:29, `evidence/evaluations/p9_final/`, `metrics_summary.txt`)
- **Correct answers:** staging 148 → 156, approved 147 → 153.
- **Misleading cards, unsupported claims, citation failures:** 0.
- **Forbidden claims on approved:** 2 → 1 (page 17's income list remains until the deletion).
- **Confident wrong-page identifications:** staging 1 → 8, approved 5 → 11 (N8 and PCC on unrelated certificate questions). Every one was traced: no card and no claim.
- **Follow-ups 17/17; probe 0/42 changed.**
- Run the suite on both databases. Compare with P1.3.
- Report per outcome class (`05`): correct, incorrect, false positives, false negatives, clarifications, abstentions, unsupported, citation failures, misleading cards.

### P2.5 Record — COMPLETE (`candidate_review_27oct.md`, `21`, `22`, `07`, `19`)
- Write each outcome into `candidate_review_27oct.md` (approved or deferred, with the reason) and into `21` and `00` §5.5.
- Write the new counts into `07` and `19`.

## P3 — Reliability verification

### P3.1 Citizen card safety, the owner's §7 list — COMPLETE (production copy: `p9_scratch_candidates/scratch_card_safety.txt`; staging traces: `p9_final/staging_regressions_traced.txt`)
- **Topics:**
  - birth, death, income, community, nativity and marriage certificates;
  - CAN editing;
  - new PAN and PAN–Aadhaar linking;
  - overseas, ordinary and electoral-roll address voter questions;
  - Aadhaar enrolment and Aadhaar update;
  - PCC;
  - new ration card.
- **How:** run on staging after P2, through the evaluator, which models the card rule: an unnamed match is shown only with verified claims.
- **Report per topic:** card shown or not, the answer, the clarification.
- **What to check:** the page 17 deletion must not turn into a false match elsewhere.
- **If a misleading card appears:** fix the general rule. Never write a page-specific rule.
- **Owner approval:** no.

### P3.2 P1-3 write-up — COMPLETE (27 Oct 22:30; trace `evidence/investigations/p9_final/p1_3_trace_staging.txt`)
- **Source:** page 19 "Register to Vote" (`https://ecisveep.nic.in/voters/general-voters`).
  - Its whole text is one paragraph of about 2,400 characters.
  - `rag.chunk_text` cuts a paragraph longer than 1,000 characters at the last space before the limit.
- **The boundary:**
  - chunk 0 (staging id 146, approved id 47) ends "… For Deletion or Objection in electoral roll";
  - chunk 1 (staging 147, approved 48) begins "fill form 7 (link to online form) Please fill Form 8 (Link to online form) for shifting of Residence/Correction of Entries in Existing Electoral Roll/Replacement of EPIC / Marking of PwD."
  - The page itself has no full stop before "Please".
- **Questions affected:** Form 7 and Form 8 questions on page 19: correcting entries, shifting residence, replacing the EPIC, marking PwD, deletion or objection. For example:
  - held-out "Which form is used to correct entries in the electoral roll?";
  - "How do I correct my name in the voter list?"

  The same boundary exists on approved.
- **Why the answer is lost (traced on staging):**
  1. The right chunk is retrieved first.
  2. The model quotes from the chunk's start: "fill form 7 (link to online form) Please fill Form 8 …".
  3. `verify_claims` keeps the quote, which is real.
  4. The meaning check rejects it, correctly: as cut, the quote ties Form 7 to correcting entries.

  For the second phrasing, the model drafts no claim at all.
- **Is it safe?** Yes. Both abstain (no claim, no wrong form). An unnamed match shows no card.
- **Future plan, separate from the migration:**
  - the sentence-aware cut prepared in `19`, "P1-3": cut after the last sentence end in the second half of the limit, else at a space as today;
  - it makes the Form 7 sentence whole in its chunk ("For Deletion or Objection in electoral roll fill form 7 …");
  - it changes the stored chunks of pages 15, 19 and 40, so it needs re-approval of those pages (page 15 is otherwise untouched) and its own staging evaluation.

  **Not done now; no re-embedding** (owner's brief §8).

### P3.3 Restart port 8000 — COMPLETE (28 Oct 10:31; new PID 89049, health and readiness OK, identify returns `named` (current code) and N8 for a birth certificate; `evidence/test_results/p9_port8000_restart.txt`)
- **Why:** PID 75965 runs code from 23 Oct.
- **How:** the procedure is in `09` (safe: no connections, last request 25 Oct). Then `GET /health/ready` and one `/api/identify` request; record the result in `21`.
- **Do not terminate** any other process.
- **Owner approval:** no.

### P3.4 Full suites at the end — COMPLETE (backend 252 OK, frontend 67, strict type check and build OK, `p9_final` suite, ingestion acceptance)
- **What:** backend, frontend, type check, production build, and the evaluation suite on both databases. Also `evaluate_ingestion.py` and the follow-up scenarios (17/17 expected).
- **State plainly** that the last browser walkthrough was automated, and that Tamil voice is untested.

### Older open reliability items (still true; low effort first)
| Item | Status | What to do |
|---|---|---|
| Overseas phrasings: 2 of 8 get no draft claim (`p6_identification/overseas_answers_approved.txt`) | Open | A prompt change was tried and **REJECTED** (it changed 5 of 16 other answers). Needs a new idea with evidence |
| 4 colloquial RC/DL misses (W11) | Open | Spelling out RC/DL for the search was **REJECTED** (it broke 6 questions). The threshold stays at 0.53 |
| Cities the code cannot place → a choice; "Lok Sabha" blocks a match | Open, safe | Clarification is acceptable |
| The abbreviation rule looks only at the top 3 pages by similarity (`rank_procedures`, `MAX_CANDIDATES`). A growing collection can push the named page out: lower-case "how do i get an idp" lost its match once the PCC page was added (28 Oct) | Open, safe (no match) | A general change (abbreviations considered beyond the top 3) changes the override for every question. Measure with the full screen first |
| Tamil Nadu certificate or registration questions without a stored page (marriage, widow, nativity, property) are identified as N8 (births and deaths); all abstain with no card | Open, safe | A document-type identification check was measured and rejected (`11` #25). Revisit only with new evidence |
| N1 Instant e-PAN deferred: a lost/duplicate PAN question can reach a misleading verified answer (`11` #57) | Open | A general change and its measurement are needed before N1 (`p9_final/candidate_review_27oct.md`) |
| APY pension amounts abstain (H2) | Open | Each claim must carry every amount in its sentence. Consider showing the whole official sentence, with tests |
| Inexact quoting by the 8B model (H4) | Open (owner: no loosening) | Possibly a larger local model (hardware decision) |
| Source gaps (H5): passport fees, PAN–Aadhaar fee amount, APY chart, UIDAI document list (PDF), citizen duplicate-licence fee | Open | Official HTML only; PDFs are a feature decision |
| Remaining ties (H6), wrong page by shared wording (W12) | Open, safe | Traces; no question-specific rules |
| EDLI page contradicts itself: ₹7 lakh vs Rs. 6,00,000 (H7) | Open | Shown as quoted, flagged partial |
| Extraction noise (M2), model variance at temperature 0 (M3), latency (M4) | Open | Low |

## P4 — Migration preparation (no production writes)
| Task | Status | Why / where | Validation |
|---|---|---|---|
| **P4.1** Field review of the 8 replacements (18, 19, 20, 27, 35, 36, 37, 38): name, department, jurisdiction, summary, eligibility, steps, URL, freshness, chunks, citations | **COMPLETE** (corrections proposed for 18, 20, 36, 37, 38: owner approval) | The owner's brief §4.2. The cards were kept from the earlier approvals, so check every claim against the staging text (read-only query; the earlier review dump was in a temporary scratchpad). Special checks below the table | Each correction is listed for the owner's approval (`19` item 2) and added to `validate_migration.py` `REVIEWED` |
| **P4.2** ID 33 (File ITR-1) assessment-year freshness | **COMPLETE** (the live page is still the AY 2025–26 guide; attribution proposed) | The card and text refer to AY 2025–26. Check the live page (read-only scrape); separate historical instructions from current guidance; no silent update | Recorded in `19`; any change goes through review |
| **P4.3** IDs 39 and 40 | **COMPLETE** | 39's step is decided. For 40, verify against the page: age 18–40, citizenship, savings account, the online eAPY route, and "is or has been an income-tax payer" (keep it) | — |
| **P4.4** Update the tooling | **COMPLETE** (self-test 12/12) | `validate_migration.py`: the expected count should follow the reference (25 + candidates); remove page 17 from `REVIEWED`; set page 39's new step. `migration_packets.py`: `(17, "Replace")` → delete; regenerate `migration_review_packets.md`. These are evidence scripts, not application code | `validate_migration_selftest.py` passes; on approved, the validator lists exactly the planned differences |
| **P4.5** Pre-flight re-scrape (`evidence/other/scripts/rescrape_dry.py` against staging) | NOT STARTED (run it right before the migration) | The live pages may have changed since 27 Oct 04:05 | Any difference is a stop condition (`19` item 5) |
| **P4.6** The 18-item approval packet (owner's brief §11) | **COMPLETE** (`22`, top section) | Most items are in `19`'s checklist and `07`. Add the final counts and checksums after P2 | The owner can approve from it alone |

**P4.1 special checks:**
- **18:** do not imply that every update can be done online.
- **19:** keep Form 6 and Form 6A distinct; check ordinary and overseas conditions.
- **20:** the voting sequence and the identity documents.
- **36, 37, 38:** wage thresholds, contributions, withdrawal conditions, pension eligibility and service, family pension, EDLI coverage and limits.
- **Remove** unsupported numerical or legal claims.

## P5 — Requires the owner's explicit approval
| Task | Status | Notes |
|---|---|---|
| **P5.1** Approve the migration plan, card values, reviewers, maintenance window (start, end) and the people who pause traffic, resume it and verify the results | **REQUIRES OWNER APPROVAL** | `19` item 7. Never invent the window or the names |
| **P5.2** Run the migration in production. Fresh `pg_dump` and restore check into a scratch database first, then add 39/40, move 16/31/32/33, delete 17, replace 18/19/20/27/35/36/37/38, `validate_migration.py --embeddings`, the suite, spot-checks, resume traffic | **REQUIRES OWNER APPROVAL** | `19` items 4–5. Stop on any failure. Never roll back automatically |
| **P5.3** Commit the uncommitted work (43 entries, including the untracked `PROCEDUREASSIST_HANDOFF/`) | **REQUIRES OWNER APPROVAL** | Risk while uncommitted: the handoff and all work since 23 Oct exist only in this working tree |
| **P5.4** N10 with a current official source (TNPDS smart-card application or e-Sevai PDS-501), if a readable official page exists | **REQUIRES OWNER APPROVAL** (a new source URL) | `candidate_review_27oct.md` |

## P6 — Future improvements (not required now)
- **Sentence-aware chunking (P1-3):**
  - its own staging evaluation first;
  - re-approval of the pages it changes;
  - never combined with the migration.
- **Database at start-up:** the backend cannot start without the database (`create_all` on import). Only a simple, justified fix; no recovery architecture.
- **Deployment hardening:**
  - **D1:** HTTPS, reverse proxy, process supervision, log rotation, monitoring, scheduled backups;
  - **D2:** revocable sessions; DNS rebinding for rendered sub-resources;
  - **D2a:** sessions held during model calls; pool sizing above about 15 concurrent requests;
  - **D3:** a security review before any release.
- **Features:** PDF sources, Tamil answers, admin review aids such as a diff when a URL is re-approved (M1).

## Completed items (history; details elsewhere)
| Item | Where recorded |
|---|---|
| Source audit, scraper, chunker and verification fixes, staging database (23 Oct) | `04`, `06`, `07`, `05` "eight-run matrix" |
| H1 document kind under colon-less lead-ins (24 Oct) | `05` "H1 fix runs", `11` #16 |
| W1 follow-up routing, W3 identifiers, W10 fee completeness, H3 fee-table rows, RC/DL attribution (25 Oct); W2 withdrawn; W11 threshold kept | `05`, `11` #17–23, `12`, `15`, `16` |
| P0-1 safety set, P0-2 scope, P1-1 periods, P1-2 code words, P3 operations, security (25 Oct) | `19`, `11` #24–31 |
| Re-extract removed, state jurisdiction, browser fallback, error pages, 11 candidates prepared (26 Oct) | `20`, `11` #32 |
| Residence rule, lower-case abbreviations, a more specific document, wider choice, PAN actions, card rule, database-outage 503, ingestion of 6 unseen URLs (27 Oct) | `20`, `21`, `22`, `11` #33–40 |
| Page 17 deletion tested and rehearsed on staging; candidates N1, N3, N4, N8 reviewed; N10 deferred; evaluation labels made unambiguous (27 Oct) | `21` (current brief), `candidate_review_27oct.md` |
