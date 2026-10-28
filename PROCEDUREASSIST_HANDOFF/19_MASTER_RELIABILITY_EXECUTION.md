# 19 — Master reliability execution (25 Oct 2026)

> **Revision, 27 Oct 2026 (evening).** By the owner's decision, **page 17 (the e-Sevai FAQ) is deleted, not replaced**. The "Final migration approval checklist" below is revised to match; it is the current operator checklist. Elsewhere in this report, statements that the page-17 replacement or rename fixes something are historical: the deletion removes those answers instead.
>
> Five candidate procedures (N1, N3, N4, N8, N10) are delegated to Claude for review and approval. They are not part of this migration; see `07` "Current state" and `evidence/investigations/p9_final/candidate_review_27oct.md`.

**Status:** complete, apart from the operations that need the owner's approval (§G). Nothing is committed, and no database was written. **Pre-migration verification (26 Oct)** resolved the report's discrepancies and finalised the migration's reviewed values; see that section. The **final migration approval checklist** follows it; the migration is not approved and not executed.

**Brief:** "Master reliability engineering and production readiness execution":
- P0-1 safety regression set;
- P0-2 identification scope;
- P0-3 source data and migration preparation;
- P1-1 claim verification;
- P1-2 abbreviations;
- P1-3 chunking;
- P3 operations;
- security.

**Method:**
- Every behaviour change was measured on both databases by the full suite (`evidence/other/scripts/run_suite.sh`).
- Each suite ran from a frozen code snapshot (`make_snapshot.sh`, `snapshot_run.py`; hashes in each run's `frozen_inputs.txt`), so every result belongs to exact code.
- Temperature 0 reproduces answers exactly: every repeat run of unchanged code was identical.

**Evidence:**
- `evidence/evaluations/master_baseline/`: today's code before any change;
- `master_safety_before/`: the safety set on the baseline code;
- `master_p0_2/`: after P0-2;
- `master_final/`: all changes.
- Investigations: `evidence/investigations/{p0_2_scope, p0_3_premigration, p1_1_verification, p1_2_abbreviations, p1_3_chunking}`.

## A. Executive summary
**Implemented (all measured, none committed):**
1. **A permanent safety regression set:** 59 cases covering every confirmed wrong answer, false match and misleading card, plus precision guards. The evaluator can now detect a confidently wrong claim (`forbidden`) and a misleading card (`card`), and it counts identification separately.
2. **Identification scope:** "US" and "UK" must appear on the page. This removed 3 of 6 confident out-of-scope matches on both databases, with no loss: answer sets are identical and three identification sets improved.
3. **Claim verification:**
   - a bare "Yes"/"No" counts only under its question, which **blocks the live wrong answer "Apprentices can become EPF members"** on the approved database;
   - a fee claimed for a test, duplicate or renewal must come from a row saying so, which **removes the fitness-test/fitness-certificate misattribution**;
   - periods keep their unit and the conditions in their quote.
   - Replayed over 441 verified claims, these rules rejected only the two wrong claims, and the answer sets are identical.
4. **Abbreviations:** a code word gives no initial (the latent "RC → REV-101" route).
5. **Operations:** request and model-call logging with a request ID; one bounded retry for transient model failures; a frontend timeout; a clear "server unreachable" message.
6. **Security:**
   - an official-domain allow-list for ingestion;
   - a check of the address actually connected to (DNS rebinding);
   - a failed-sign-in limit;
   - non-ASCII tokens rejected cleanly (401, not 500).
7. **Migration preparation:** the live pages have not drifted since staging was built, so the staging results are evidence for exactly the text a migration would approve. A read-only validation script and the reviewer's correction list are ready.

**Still unresolved:**
- **Two live wrong answers remain on approved data**, both from page 17's unlabeled document lists and both shown under its misleading card (traced 26 Oct, see "Pre-migration verification"):
  - the TN income-certificate answer is 1 item, "Proof of Income (Payslip, Income Certificate, etc)", from the Deserted Women list;
  - the nativity-certificate answer has 8 items, 3 of them from other lists.
- **Only the migration fixes these.** Staging gives the correct 9 and 5 items, but shows the old page-17 card until the reviewer renames it. (Superseded 27 Oct: page 17 is deleted, so neither the lists nor the card remain.)
- "Marriage certificate" and "change the name on my PAN card" still match a related page, whose answer abstains.
- The four W11 colloquial or abbreviated misses remain safe no-matches.

**Ready to deploy?** **No.** It is a sound, much safer base, but not production-ready until:
- the migration is approved and run (two live wrong answers and a misleading card);
- the deployment work in §H is done: HTTPS, a process supervisor, a reverse proxy, a database pool sized for concurrency, and session revocation if needed.

## B. Phase completion

| Phase | Status | Changes | Tests | Remaining issues |
|---|---|---|---|---|
| Reconnaissance and baseline | Completed | — | Backend 221, frontend 63, tsc, build; all 10 suite runs reproduced exactly | — |
| P0-1 safety set | Completed | `safety.json`; evaluator keys | Run on both databases, before and after every change | The two marriage cases need the owner's confirmation (`review`) |
| P0-2 scope checks | Completed | `procedure_search.mentions` / `_decide` | 3 unit + 1 API test; full suite | Marriage and PAN-name matches (no regression-free rule found); W11 misses |
| P0-3 data and migration | **Partially completed (blocked by approval)** | Pre-check; `validate_migration.py`; review list | Validation run on both databases | The migration itself needs approval (§G) |
| P1-1 verification | Completed | `rag.verify_claims` (3 rules) | 3 unit tests; 1 test updated deliberately; replay; full suite | A quote cut before its condition |
| P1-2 abbreviations | Completed | `abbreviates` | 1 unit test; 144 questions decided | PAN override and DL/RC spelling: measured, not changed |
| P1-3 chunking | Investigated; change **held** | None (a prepared variant) | In-memory simulation | Re-embeds 3 pages: the owner's choice, with the migration |
| P3 operations | Completed (code) | `main.py` logging; `extractor.ollama_post`; `api.ts` timeout; `App.tsx` | 4 backend + 2 frontend tests | Database session held during model calls (pool pressure under load): documented |
| Security | Completed (code) | Allow-list, connected-address check, login limit, byte comparison | 6 tests; live check | HTTPS, proxy, session revocation, sub-resource rebinding: deployment items |

## Pre-migration verification (26 Oct 2026)
Read-only; no database written (checksums identical before and after); no migration; nothing committed.

**Discrepancies found and resolved:**
1. **The certificate answers.** The executive summary named two live wrong answers on approved data (income and nativity lists); the final table counted only the nativity list.
   - **Cause:** the evaluator checked the card before the claims, so the wrong income claim was reported as "misleading card".
   - **Fixed:** in the evaluator (the forbidden claim is reported first, with the card noted). Re-run, the counts are unchanged and the labels are right.
2. **Page 17's name.** `07` still proposed "Tamil Nadu e-Sevai: CAN and certificate documents (FAQ)", against this report's "e-Sevai FAQ: CAN and certificate documents". Now one name everywhere.
3. **Page 40's eligibility.** The proposed "have never been" wording would have failed the validator's "has been" check. It is now one exact sentence using the page's own "is or has been".
4. **Page 39's example step** cited Rule 81, which page 39 does not state. Replaced.
5. **The page count wording.** "15 pages (re-)approved" and "9 kept pages" are now "13 existing pages moved or re-approved, 2 new, 11 untouched". Of the 11, 9 gain only a label on re-scrape and 2 are identical.
6. **The validation baseline in `07`** still pointed at the H1-era results and hashes. It now points at the final-code runs.

**The two certificate questions** (`p0_3_premigration/certificate_trace.py`; the real API with the final code; the trace reproduces the suite's claims exactly):

| | Approved: income certificate | Approved: nativity certificate | Staging: income | Staging: nativity |
|---|---|---|---|---|
| Procedure selected | 17, "REV-101 Community Certificate" | 17 | 17 | 17 |
| Card displayed | **Yes**: that name, with the 11 CAN-editing steps | **Yes**, the same | **Yes**, the same (rename pending) | **Yes**, the same |
| Model's draft | 2 claims | 8 claims | 9 | 5 |
| `verify_claims` | Kept 1. Rejected "Proof of Income…" quoting "Salary Certificate (Latest Copy)": its document kind (income) is not in the quote. | Kept all 8 | Kept 9 | Kept 5 |
| Meaning check | Kept 1; complete = false | Kept 8; **complete = true** | Kept 9 | Kept 5 |
| Final claims (quote = text) | "Proof of Income (Payslip, Income Certificate, etc)" (chunk 35; from the Deserted Women list) | Photo; Address Proof; **Community Certificate of Father…**; Birth Certificate; School Education Certificate… continuous residence; Self-Declaration; **Income Tax Return**; **Proof of Income…** | The 9 FAQ-9 items | The 5 FAQ-8 items |
| What the citizen sees | The card, then 1 item and the note "The official text found may not cover every part of your question." | The card, then 8 items, no partial note | The card, then 9 items | The card, then 5 items |
| Verdict | **Incorrect** (not part of the income list) | **Incorrect** (3 of 8 items from other certificates) | Correct; card misleading | Correct; card misleading |

**Why approved has 53 safety cases and staging 59.** Six cases need page 39 (`requires: ["fees-and-user-charges"]`), which only staging has. On approved they are skipped and reported as such, not counted:
1. "How much does a duplicate RC cost?"
2. "What is the fee to renew the registration certificate of my motorcycle?"
3. "What is the fee to renew the RC of a motorcycle?" (asked inside page 39)
4. "What is the fitness test fee for a motorcycle?"
5. "What is the hypothecation endorsement fee for a car?"
6. "What is the RC renewal fee for an imported car older than 20 years?" (asked inside page 39)

They will apply to approved once the migration adds page 39.

**Validator revised** (`evidence/other/scripts/validate_migration.py`, still read-only):
- It refuses `procedureassist_staging`.
- It checks every card field against the reviewed values (pages 17, 39, 40) or the unchanged current card (all other pages).
- It checks vector count, dimensions, finiteness and non-zero norm before cosines.
- It compares FAQ question-answer pairs with staging.
- It checks total chunks.
- Both sessions are read-only and engines are disposed.

`validate_migration_selftest.py` applies the reviewed values to the staging records in memory: 0 failures, and all 11 deliberate faults caught. On approved before migration it reports 30 failed checks, exactly the pages and cards the migration changes. The 11 untouched pages already pass.

**Evidence note:** `p0_3_premigration/validate_staging_selfcheck.txt` (the first validator's staging run) was deleted by mistake on 26 Oct. It was regenerated by re-running that exact first version read-only; the result is identical (3 failed checks, the outstanding corrections).

## Final migration approval checklist (NOT approved; NOT executed; revised 27 Oct 2026 for the page 17 deletion)
This checklist turns `07` ("Current state", "Reviewed card values", "Proposed migration") into the exact operations. Nothing here has been run on the approved database. **It needs the owner's written approval of the decisions in item 7.**

**Rehearsed on staging, 27 Oct.** Page 17 was deleted from `procedureassist_staging` through the same admin route, after a backup. Staging is now the 25-page target.

**Tooling to update first** (`10`, P4; not yet done):
- `evidence/other/scripts/validate_migration.py` still expects 26 pages and the old page-17 card in `REVIEWED`, and page 39's old step.
- `evidence/investigations/p7_migration/migration_packets.py` still lists page 17 as "Replace".

### 1. The 25-page plan (was 26)
**14 pages are approved through the workflow and 1 page is deleted.**
- The admin workflow embeds the 14 pages' 102 chunks.
- The 90 chunks of the replaced, moved and deleted records are removed by cascade.

| # | Approved ID | Page | Action | URL after migration | Chunks after |
|---|---|---|---|---|---|
| 1 | new | Vehicle Registration Fees and User Charges | **Add** | `https://parivahan.gov.in/en/content/fees-and-user-charges` | 12 |
| 2 | new | Atal Pension Yojana (PFRDA scheme details) | **Add** | `https://www.pfrda.org.in/schemes/atal-pension-yojana-apy` | 4 |
| 3 | 16 | Filing of ITR-2 | **Move**: approve the new URL, then delete the old record (`…itr-2-UM?mobile-app=1&utm_source=chatgpt.com`) | `https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/file-itr-2-online/itr-2-UM?mobile-app=1` | 19 |
| 4 | 31 | Link PAN with Aadhaar | **Move** (old: without `?mobile-app=1`) | `https://www.incometax.gov.in/iec/foportal/help/how-to-link-aadhaar?mobile-app=1` | 8 |
| 5 | 32 | Register on the e-Filing Portal | **Move** | `https://www.incometax.gov.in/iec/foportal/help/how-to-register-e-filing?mobile-app=1` | 3 |
| 6 | 33 | File ITR-1 (Sahaj) Online | **Move** | `https://www.incometax.gov.in/iec/foportal/help/how-to-file-itr1-form-sahaj?mobile-app=1` | 17 |
| 7 | 17 | REV-101 Community Certificate (the e-Sevai FAQ) | **Delete** (Saved procedures → Delete; owner decision 27 Oct). No re-approval | — (none after) | 0 |
| 8 | 18 | Updating Data on Aadhaar | **Replace** | `https://uidai.gov.in/en/updating-data-on-aadhaar` | 11 |
| 9 | 19 | Register to Vote | **Replace** | `https://ecisveep.nic.in/voters/general-voters` | 3 |
| 10 | 20 | How to Vote | **Replace** | `https://ecisveep.nic.in/voters/how-to-vote` | 6 |
| 11 | 27 | Driving Licence Fees and Charges | **Replace** | `https://parivahan.gov.in/en/content/licensing-related-fees-charges` | 2 |
| 12 | 35 | Aadhaar Enrolment and Update at Post Offices | **Replace** | `https://www.indiapost.gov.in/otheronlineservices/aadhaar-updation` | 3 |
| 13 | 36 | Employees' Provident Fund Scheme | **Replace** | `https://www.epfo.gov.in/epf-scheme` | 5 |
| 14 | 37 | Employees' Pension Scheme (EPS) | **Replace** | `https://www.epfo.gov.in/pension-scheme-eps` | 5 |
| 15 | 38 | Employees' Deposit Linked Insurance (EDLI) | **Replace** | `https://www.epfo.gov.in/insurance-scheme-edli` | 4 |

**11 pages are untouched**, with no action of any kind (32 chunks, embeddings unchanged): 15 Passport, 21 Overseas (NRI) Voter Registration, 22 Learner's Licence, 23 Permanent Driving Licence, 24 Renewal of Driving Licence, 25 Duplicate Driving Licence, 26 International Driving Permit, 28 Renewal of Vehicle Registration Certificate, 29 Change of Address in Vehicle Registration, 30 Transfer of Vehicle Ownership, 34 Atal Pension Yojana.

**Result:** 25 pages, 134 chunks (32 + 102); this is staging today.
- **Ids are per database.** "39" and "40" in this checklist are the staging ids of the two additions. In the approved database they will get the next free ids; the delegated candidates took 39–42 in the scratch copy. The URL identifies each page; `validate_migration.py` compares by URL.
- **Delegated candidates (done 28 Oct):** N3, N4 and N8 were approved into both databases (N1 and N10 deferred). So the migration's result is **28 pages / 146 chunks**, equal to staging now. They are untouched by the migration: their text, card and chunks are already identical in both databases (validator, 28 Oct 09:36).
- **Live changes:** the total may differ only if a live page changes before approval; `validate_migration.py` then fails on that page's text.

**Card rule:**
- Pages 3–6 and 8–15 keep their current card exactly (name, department, jurisdiction, summary, eligibility, steps). Replace the model's fresh draft with the current values, from `procedureassist_staging` or from the approved record before it is deleted.
  - Exception: a value corrected by the pending field review of the 8 replacements (`10`, P4). Such a correction must be added to item 2 and to `validate_migration.py` `REVIEWED` before the migration.
- Pages 1 and 2 use the values in item 2. Page 7 (id 17) is deleted.

### 2. Card metadata for pages 39 and 40 (page 17 removed: it is deleted)
These are the same values as `07` "Reviewed card values" and `validate_migration.py` `REVIEWED` (checked against each other on 26 Oct).
- **Exception:** page 39's step changed on 27 Oct and is **not yet** in `REVIEWED`.
- For pages 39 and 40, the fields the plan does not correct are reproduced exactly from the staging records (read 26 Oct): the name, department, jurisdiction and summary of both pages, and page 40's three steps.
- Nothing here is reworded.

**Proposed card corrections from the 27 Oct field review (owner approval pending):**
- **Pages:** 18 (route labels), 20 (SMS format, the 12 accepted IDs), 33 (assessment year attributed to the official guide), 36 (summary; nomination is not an online service), 37 (disablement pension without 10 years) and 38 (the page's two maximum benefits; coverage).
- **None needed:** 19, 27, 35.
- **Exact values and reasons:** `evidence/investigations/p9_final/replacement_field_review.md`.
- **If approved:** add them to `validate_migration.py` `REVIEWED` and regenerate the packets before the migration. **If not:** the current cards stay, as in the card rule.

**Page 17: deleted (owner decision, 27 Oct).** It has no card. The values that follow were the earlier replacement proposal and are kept only as a record. **Do not enter them.**

**Page 17, superseded proposal** (`https://tnesevai.tn.gov.in/Citizen/FAQ.html`):

| Field | Value |
|---|---|
| name | e-Sevai FAQ: CAN and certificate documents |
| department | Information Technology and Digital Services Department |
| jurisdiction | Tamil Nadu |
| summary | Frequently asked questions from the Tamil Nadu e-Sevai portal: what a Citizen Access Number (CAN) is and how to find or edit it, the documents required for community, nativity, income, solvency, no male child, unmarried, inter-caste marriage, widow, OBC and deserted women certificates, and how to check an application's status and find returned applications. |
| eligibility | A Citizen Access Number (CAN) is required to avail e-Sevai services. |

Steps (11, official FAQ 6 wording; only step 1 adds "To edit your CAN details,"):
1. To edit your CAN details, go to https://www.tnesevai.tn.gov.in/ on your web browser.
2. In the Sign In section, click on "Citizen Login".
3. Enter the login credentials.
4. Correctly enter the Captcha Code (Not case sensitive) and click on "Login".
5. In the "Services" tab, select "DEPARTMENT WISE" and then click on "Revenue Department".
6. Click on "REV-101 Community Certificate". This will open a new browser tab.
7. Click on the "Proceed" button.
8. In this Search section, look for your CAN using any of the six fields provided.
9. Once found, select it by clicking the Radio button. This will auto-fill the "Mobile Number" field at the bottom.
10. Click on "Generate OTP" and then enter the OTP that has been sent to your registered phone number. Click on "Confirm OTP" once done.
11. Now you will be able to see the "Edit CAN Detail" button. Click it and you will be able to update your CAN details.

**Page 39** (`https://parivahan.gov.in/en/content/fees-and-user-charges`):

| Field | Value |
|---|---|
| name | Vehicle Registration Fees and User Charges |
| department | Ministry of Road Transport and Highways (Parivahan) |
| jurisdiction | India |
| summary | This document outlines various fees and user charges associated with different government procedures related to motor vehicles, including trade certificates, registration, renewal, and other vehicle-related services. |
| eligibility | none (empty) |
| steps (1) | **Refer to the fee table to identify the applicable fee for the relevant vehicle-related service.** (owner decision, 27 Oct; replaces "Find your service in the table and pay the amount listed against it.", which the page does not state) |

**Page 40** (`https://www.pfrda.org.in/schemes/atal-pension-yojana-apy`):

| Field | Value |
|---|---|
| name | Atal Pension Yojana (PFRDA scheme details) |
| department | Pension Fund Regulatory and Development Authority (PFRDA) |
| jurisdiction | India |
| summary | The Atal Pension Yojana (APY) is a pension scheme introduced by the Government of India in 2015 to provide a universal social security system for Indian citizens, particularly the poor, under-privileged, and workers in the unorganised sector. |
| eligibility | All Indian citizens with savings bank accounts in banks or Department of Posts, aged between 18 and 40 years. From 1st October, 2022, any citizen who is or has been an income-tax payer is not eligible to join APY. |

Steps (3):
1. Fill out the APY Registration Form, which is available at bank branches and post offices.
2. Submit the form to the corresponding bank branch or post office.
3. Alternatively, join online through eAPY by clicking the provided link.

### 3. Reviewer assignment
**Owner and approval authority:** Arun N M (Arun-N-M-07). He makes the final migration decision.

**Evidence used:**
- **Git history (all branches).** Three human contributors: Arun-N-M-07 (27 commits), BBoomitha (3) and Sharmila027 (4). No contributor, CODEOWNERS or reviewer file exists.
- **BBoomitha:**
  - `db9a13e` "Improve government source extraction": scraper, `SourcePreview.tsx`;
  - `38ae859`: scraper formatting;
  - `30ff110`: scraper regression tests, including URL normalisation (ports, fragments, trailing slashes).
- **Sharmila027:**
  - `630dbf1` "Complete Member 3 procedure extraction and admin review": `ProcedureReview.tsx`, plus a sample source fixture for a **Tamil Nadu Revenue Department income certificate**;
  - `02f8ee8`: extractor error handling;
  - `ca4c698`: admin procedure API validation;
  - `55f37c8`: health check.
- **Independence:** neither implemented the changes under review. Those were made on Arun's branch: the 23–25 Oct scraper fixes that changed the pages' text, the URL moves, and the reviewed card values.
- **Not established for anyone:** familiarity with the specific EPFO, UIDAI, ECI, Parivahan, income-tax, India Post or PFRDA procedures, and with the evaluation and validation tooling.
- **Availability and agreement:** not established for any proposed reviewer; Arun must confirm.
- **Access:** the admin page has a single admin account, so how reviewers reach it is Arun's decision.

| # | Page | Reviewer | Basis | Rationale | The reviewer checks |
|---|---|---|---|---|---|
| 1 | 39 Vehicle Registration Fees and User Charges (add) | Sharmila027 | **Evidence-based** | Built the extraction and admin-review screen, so knows the card fields; did not write these values. Familiarity with the fee procedures is not established. | Extracted text equals staging; card exactly as item 2 |
| 2 | 40 Atal Pension Yojana (PFRDA scheme details) (add) | Sharmila027 | **Evidence-based** | As row 1 | As row 1; especially the eligibility sentence |
| 3 | 16 Filing of ITR-2 (move) | BBoomitha | **Evidence-based** | Wrote the government source extraction and its URL-normalisation tests; did not make the move decision. Familiarity with income-tax manuals is not established. Caveat: she wrote part of the earlier scraper, but this page's text was produced later by others' fixes. | New URL saved with text equal to staging and the current card; old record deleted after |
| 4 | 31 Link PAN with Aadhaar (move) | BBoomitha | **Evidence-based** | As row 3 | As row 3 |
| 5 | 32 Register on the e-Filing Portal (move) | BBoomitha | **Evidence-based** | As row 3 | As row 3 |
| 6 | 33 File ITR-1 (Sahaj) Online (move) | BBoomitha | **Evidence-based** | As row 3 | As row 3 |
| 7 | 17 e-Sevai FAQ (**delete**; revised 27 Oct) | The person running the migration (Arun N M decides) | Owner decision | No content to review: the record is removed | After the delete: 25 pages; no page with `tnesevai.tn.gov.in`; no orphan chunks |
| 8 | 18 Updating Data on Aadhaar (replace) | BBoomitha | **Evidence-based** | Source-extraction familiarity fits the check, which is that the re-scraped text is complete and equals staging. She did not implement the fixes that changed it. Familiarity with the procedure is not established. | Text equals staging; current card kept |
| 9 | 19 Register to Vote (replace) | BBoomitha | **Evidence-based** | As row 8 | As row 8 |
| 10 | 20 How to Vote (replace) | BBoomitha | **Evidence-based** | As row 8 | As row 8 |
| 11 | 27 Driving Licence Fees and Charges (replace) | BBoomitha | **Evidence-based** | As row 8 | As row 8; one fee row per paragraph |
| 12 | 35 Aadhaar Enrolment and Update at Post Offices (replace) | BBoomitha | **Evidence-based** | As row 8 | As row 8 |
| 13 | 36 Employees' Provident Fund Scheme (replace) | BBoomitha | **Evidence-based** | As row 8 | As row 8; each FAQ question directly above its answer |
| 14 | 37 Employees' Pension Scheme (EPS) (replace) | BBoomitha | **Evidence-based** | As row 8 | As row 13 |
| 15 | 38 Employees' Deposit Linked Insurance (EDLI) (replace) | BBoomitha | **Evidence-based** | As row 8 | As row 13 |
| — | Final migration validation (item 4, steps 6–7) | Arun N M | **Fallback: independent review unavailable** | No other contributor has evidence of working with `validate_migration.py` or the evaluation suite; both were produced on Arun's branch. Arun is also the owner. | `validate_migration.py --embeddings` reports 0 failed checks; suite results match staging; browser spot-checks pass |

### 4. Sequence of operations, maintenance window and traffic pause
**Maintenance window.** The owner fills these in; they are unknown, so they are left blank.

| Field | Value |
|---|---|
| Maintenance date | ________ |
| Start time (IST) | ________ |
| Expected duration | ________ (not measured) |
| Person responsible for pausing and resuming citizen traffic | ________ |

**Traffic pause (required):**
- Citizen-facing traffic (the citizen page and the citizen API routes) is paused before step 3, and **stays paused through the move and replacement stages (steps 3–4) and the validation (steps 6–7)**.
- The admin page stays available to the reviewers. How traffic is paused depends on the deployment and is set by the responsible person.
- **Traffic may resume only after** the migration is complete, `validate_migration.py --embeddings` reports 0 failed checks, the suite results match staging and the browser spot-checks pass, **and Arun N M authorises resumption**.

Each page goes through the admin page: Extract → review → Approve. No script writes to the approved database.
1. **Pre-flight (read-only):**
   - application code hashes equal `evidence/evaluations/master_final/frozen_inputs.txt`;
   - re-run the pre-migration re-scrape (`evidence/other/scripts/rescrape_dry.py`, with `DATABASE_URL` set to staging), since the last one was 25 Oct 18:00. Any page whose text differs from staging is a failure (item 5).
2. **Step 0, backup:** see item 5. **Do not continue without a verified backup.** Then pause citizen traffic.
3. **Steps 1–2, add pages 39 and 40.**
4. **Step 3, move 16, 31, 32, 33.** For each: approve the new URL, then delete the old record. For the seconds between the two actions, both records exist; with traffic paused, no citizen sees this.
5. **Step 4a, delete page 17** (revised 27 Oct): in "Saved procedures", delete "REV-101 Community Certificate" (`https://tnesevai.tn.gov.in/Citizen/FAQ.html`). Nothing replaces it. Check: 4 chunks gone, no orphans.

   **Step 4b, replace 18, 19, 20, 27, 35, 36, 37, 38.** The URL is unique, so the old record must be deleted before the new one is saved. For each page:
   1. Extract and review the draft while the old record still exists.
   2. Delete the old record in "Saved procedures".
   3. Press Approve immediately.
   - The review form keeps its draft while the list deletes, because they are separate components.
   - The page is missing from the database from the delete until Approve finishes embedding its 2–11 chunks: usually seconds (not measured).
   - The provenance token expires 2 hours after Extract, so approve within 2 hours.
6. **Validation (read-only):**
   - `validate_migration.py --embeddings`: expect **0 failed checks** (28 pages and 146 chunks as staging, after the 28 Oct approvals; text, cards, FAQ pairs, vectors). The script was updated 27 Oct (self-test 12/12). Add any approved field-review corrections to `REVIEWED` first;
   - then the full evaluation suite, compared with a **fresh staging run on the same code and labels**. The 25 Oct `master_final/` and `premigration_safety/` results predate the deletion and the label changes.
7. **Spot-check in the browser:**
   - EPF apprentices;
   - birth, death, community and income certificate questions: no CAN-editing steps, and no unrelated card;
   - the IDP fee, motorcycle RC renewal and polling steps.
8. **Resume citizen traffic** only as stated under "Traffic pause".

### 5. Fresh backup, failure handling and rollback
**Fresh backup (step 0; required):**
- Run `pg_dump -Fc procedureassist -f /Users/arunnm/Projects/SOP-backups/procedureassist_<date>_before_migration.dump`.
- Verify it with `pg_restore -l <dump>`.
- Record its SHA-256, and the pre-migration checksums from `evidence/database/db_checksums.sql`.
  - They must equal approved `016980ee…` / `3e45c78f…` (24 pages, 122 chunks) unless the database legitimately changed.
  - The delegated candidate approvals are such a change. After them (28 Oct 09:34) approved is **27 pages / 134 chunks, `750d4dc2f448e94373f8eb509b339fe2` / `e7fee54863a0304e9455ce09edaf4a69`**. Use these unless it changes again (`21`).
- **Restore check** (revised 27 Oct; required by the owner's brief): restore the fresh dump into a new scratch database (`createdb`, `CREATE EXTENSION vector`, `pg_restore`). Its checksums must equal the source's. Then drop only that scratch database. Done this way on 27 Oct (`evidence/database/restore_check_27oct.txt`; `21`).
- The dump stays out of the repository.
- This fresh, verified dump is the only rollback source for this migration. The staging database and the 23 Oct dump are not.

**If any operation or validation fails** (an Extract, Approve or delete error; a text that differs from staging; a failed validator check; a suite result worse than staging; a failed spot-check):
1. **Stop all migration activity.** Citizen traffic stays paused.
2. **Preserve the current state and collect evidence.** Make no further deletes, approvals or edits. Record:
   - the step and page;
   - error messages and screens;
   - the server log lines with their request IDs;
   - the `validate_migration.py` output;
   - read-only checksums of the approved database.
3. **Investigate the cause read-only.** Make no database change that has not been approved.
4. **Present the failure and the recovery options to Arun N M:**
   - what failed;
   - which pages are done, pending or missing;
   - the evidence;
   - the options, such as retrying one page after a fix, holding, or a full rollback.
5. **Get Arun N M's explicit decision before a full database rollback.** Nothing is dropped, recreated or restored automatically.
6. **If, and only if, rollback is authorised,** restore the fresh verified pre-migration dump. With the backend stopped, run in order:
   1. `dropdb procedureassist`
   2. `createdb procedureassist`
   3. `psql -d procedureassist -c "CREATE EXTENSION IF NOT EXISTS vector"`
   4. `pg_restore -d procedureassist <the fresh dump>`

   Then confirm the checksums equal the values recorded at step 0.

**Never save staging text by script.**

### 6. Explicitly excluded from this migration
- **Sentence-aware chunk splitting** (P1-3) is excluded. `rag.chunk_text` stays as it is, and pages 15, 19 and 40 are chunked as on staging.
- **All optional or additional re-embedding is excluded.** The only embedding permitted is the normal generation the admin workflow performs when approving each of the 14 approved pages (102 chunks). The 11 untouched pages keep their stored chunks and embeddings, and the deleted page 17 has none.
- No change to `.env`, the evaluation expectations, the source procedures beyond this plan, or the scripts.

### 7. Decisions still required from Arun N M
1. **Approve this plan**: the page 17 deletion, the 14 page actions and the 11 untouched pages (item 1), and the sequence (item 4).
2. **Approve the card values** for pages 39 and 40 (item 2). Page 39's step was decided by the owner on 27 Oct. Also approve the rule that every other card stays exactly as it is, except corrections from the pending field review (`10`, P4), which will be listed for approval.
3. **Confirm the proposed reviewers** (item 3), or replace them:
   - Sharmila027 and BBoomitha must agree and be available;
   - decide how they reach the single-account admin page.
4. **Fill in the maintenance window** (item 4): date, start time (IST), expected duration, and the person responsible for pausing and resuming citizen traffic.

**During the migration**, Arun N M also authorises resuming traffic, and decides on any rollback after a failure (items 4 and 5).

## P0-1 — Permanent safety regression set

**Files:**
- `fixtures/evaluation/safety.json` (new; 59 cases);
- `scripts/evaluate_answers.py` (additive keys).

**Existing fixtures are unchanged; their scoring is unchanged.** None of them uses the new keys. The totals line uses the number of cases run, which equals the number of cases when none is skipped.

**New evaluator keys:**
- `forbidden`: a pattern no claim's own text may match. This catches a confidently wrong answer, such as "Apprentices can become EPF members".
- `card`: a pattern the matched procedure's card (name, summary, steps, eligibility) must not match. This catches page 17's CAN-editing card under a Community Certificate name.
- `requires`: pages the case needs. Page-39 cases are skipped on approved data until the migration adds it.
- **Identification summary:** a separate line counting correct, confident wrong page, missed, asked, and unexpected clarification.
- **`--claims`:** prints every final claim as JSON (text, quote, chunk) for review and offline rule replay.

**Coverage (category: cases):**
- **A. Jurisdiction and location (10):** the UK licence and US passport false matches; Dubai and other residence cases that must still reach the overseas-voter page; IDP trips to the USA or UK.
- **B. Document type (7):** marriage certificate ×2 and PAN name change (the false matches); TN income-certificate list attribution, with the page-17 card check; community, nativity and RC precision guards.
- **C. Identification misses (4):** the W11 misses (the threshold stays 0.53).
- **D. Source data (4):** EPF apprentices; two other EPF FAQ answers lost on approved data; the page-30 heir condition.
- **E. Verification (11):** rows 4(b), 9(b), 10(a) against 11, and 16(f) on page 39; DL renewal and IDP fees; Form 6A; NRI and ITR-1 negation; the renewal-date condition.
- **F. Follow-ups (10):** W1 switches and stays; W10 completion; H4.
- **G. Out of scope (6).**
- **H. Precision guards (7):** "Indian", "Bengaluru", TN/CAN, DL, EDLI, PF, IDP.

**Expectations come only from stored official text** (each case's `note` cites it). Two cases are marked `review` because they need the owner's confirmation: the marriage-certificate pair. Page 17 lists documents for an *Inter Caste* Marriage Certificate only, so a general marriage certificate is treated as out of scope.

**What it cannot test:** the card for every matched page. Only cases with `card` check it; page 17's card is covered by the income-certificate case and by `validate_migration.py`. Unit-level verification classes (number words, identifiers, back-references, money per row) stay in `tests/test_guidance.py`, because an end-to-end question cannot force the model to make those errors.

## P0-3 — Source data and migration preparation

**Approval gate verified in code:**
- The model's draft is only returned to the admin page (`routes.create_extraction`).
- Saving needs the reviewer's explicit "Approve and save" submit (`AdminPage.handleApprove`), a valid admin session (`admin_router` → `require_admin`), and an HMAC provenance token tying the exact URL and text to a recent server-side extraction (`_verify_provenance`).
- Nothing the model produces is saved by itself.

**Pre-migration check (read-only, run 25 Oct 18:00; `p0_3_premigration/rescrape_vs_staging.*`):** all 26 staging URLs were re-scraped with today's scraper.
- The 13 existing pages the plan moves or re-approves (17–20, 27, 35–38 re-approved; 16, 31–33 moved), and the 2 new pages (39, 40), give **exactly** their staging text: 0 paragraphs removed or added, same final URL.
- Of the 11 untouched pages, 9 differ only by one label paragraph, as `07` predicted ("View PDF" on 22–26 and 28–30; "Jansuraksha Scheme" on 34). Pages 15 and 21 are identical.
- **So the staging evaluations are evidence for exactly the text a migration would approve.**

**Review list for the migration (the reviewer's corrections; proposals only, from the pages' own text).** The exact values, including all 11 steps, are in `07`, "Reviewed card values". `validate_migration.py` enforces the same values. Every page not listed keeps its current card exactly.

| Page | Field | Today (approved and staging) | Proposed | Why |
|---|---|---|---|---|
| 17 TN e-Sevai FAQ | name | "REV-101 Community Certificate" | "e-Sevai FAQ: CAN and certificate documents" (jurisdiction stays "Tamil Nadu") | The page is an FAQ about the Citizen Access Number (CAN) and the documents for 10 certificates. Avoid "Tamil Nadu" in the name: its initials "TN" would make every "TN" question an abbreviation match for this page (`_decide`). The current name's initials already make "RC" match it (non-own `abbreviates`). |
| 17 | summary | "allows users to generate an OTP and edit their CAN details … REV-101 Community Certificate service" | "Frequently asked questions from the Tamil Nadu e-Sevai portal: what a Citizen Access Number (CAN) is and how to find or edit it, the documents required for community, nativity, income, solvency, no male child, unmarried, inter-caste marriage, widow, OBC and deserted women certificates, and how to check an application's status and find returned applications." | Covers FAQ 1–18; asserts no procedure the page lacks |
| 17 | eligibility | "Users must have a registered phone number and valid login credentials" | "A Citizen Access Number (CAN) is required to avail e-Sevai services." (FAQ 2) | From the page |
| 17 | steps | 11 CAN-editing steps, under a Community Certificate name | The 11 steps of FAQ 6 word for word (official double quotes), the first reading "To edit your CAN details, go to https://www.tnesevai.tn.gov.in/ on your web browser." | Verified 26 Oct: today's 11 card steps equal FAQ 6 paragraph by paragraph. They edit a CAN; they do not apply for a certificate. |
| 39 Rule 81 fee table | steps | 16 "Payment of fees for …" lines (a fee list, not steps) | One step: "Find your service in the table and pay the amount listed against it." | Card accuracy. **Corrected 26 Oct:** the earlier example cited "Rule 81 of the Central Motor Vehicle Rules, 1989", which page 39's own text does not state (pages 28–30 do). |
| 39 | name / department | Set by SQL in staging | "Vehicle Registration Fees and User Charges"; "Ministry of Road Transport and Highways (Parivahan)" (as page 27) | Never reviewer-approved; the staging name is kept so identification behaves as evaluated |
| 40 PFRDA APY | eligibility | "All Indian citizens … aged between 18 and 40 years, who are not income-tax payers from 1st October, 2022." | "All Indian citizens with savings bank accounts in banks or Department of Posts, aged between 18 and 40 years. From 1st October, 2022, any citizen who is or has been an income-tax payer is not eligible to join APY." | The page: "any citizen who is or has been an income-tax payer, is not eligible to join APY". **Corrected 26 Oct:** the earlier "have never been" wording would have failed the validator's check. |

**Defects in the official pages themselves (cannot be corrected by us; for the reviewer to note):**

| Page | Official text | Effect |
|---|---|---|
| 17 FAQ 15 / 16 | "OBC certificate" lists Proof of Marriage, Proof of Desertion or FIR; "Deserted Women certificate" lists Proof of Income, Community Certificate, Income Tax Return | The two lists look swapped on the official page. Answers quote them as published. |
| 36 EPF FAQ | "What happens to contributions if the employer becomes insolvent?" → "Yes" | A meaningless answer. A claim quoting it says nothing reliable. |
| 37 EPS FAQ | "diability pension" | Typo. A quote that corrects it fails the exact-quote check (safe). |
| 21 Overseas voters | Heading "Documents required with Form 6?" above Form 6A documents | Mislabelled heading. W3 checks identifiers against quote and heading. |
| 30 Ownership transfer | "Where the owner ofa motor vehicle dies" (verified in the raw HTML); headings joined to their text (`<li><span class="font-bold">…</span><br><span>…</span></li>`) | Typo: an exact quote must keep it. The joined headings are the page's own markup; no failure traces to them, so the scraper is left alone. |

**PDF ingestion:** not supported (`scraper.HTML_CONTENT_TYPES`). Adding it needs a PDF text extractor (a new dependency) and table handling. No reliability objective here depends on a PDF source, so it stays a separate future enhancement.


## P0-2 — Identification scope checks

**Investigation:** `p0_2_scope/scope_variants.py` (embeddings only). It decided 203 staging and 199 approved distinct labelled questions on the whole message. Four synthetic probes with non-place capitals were added, in the simulation only.

| Variant | Staging, in scope: correct / missed | Out-of-scope false matches | Approved, in scope: correct / missed | Out-of-scope false matches |
|---|---|---|---|---|
| Today | 154 / 9 | 6 | 152 / 8 | 6 |
| Any two-letter capital is a place name | 152 / 11 | 3 | 150 / 10 | 3 |
| **"US"/"UK" + own abbreviation (chosen)** | **154 / 9** | **3** | **152 / 8** | **3** |
| + document named on the page | 149 / 15 | 3 | 145 / 16 | 1 |
| + Title-Case qualifier = another document | 140 / 24 | 1 | 136 / 25 | 1 |

**Why only "US" and "UK":**
- Longer place names ("Dubai", "Canada", "USA") are already names that `mentions` checks.
- Only the two-letter country abbreviations escaped its three-character minimum.
- Treating every two-letter capital as a place lost "SC certificate" (TN community certificates), "IT return" and "Is it OK…".

**Why no document check:** it removed the marriage-certificate match only at the cost of 5–16 correct matches. Page 17 does name an "Inter Caste Marriage Certificate", so text alone can't tell the documents apart.

**Change:** `procedure_search.COUNTRY_CODE`. In `mentions`, "US"/"UK" must appear on the page as written (not from "contact us"; skipped for questions written in capitals throughout). A name that the candidate's own name or jurisdiction abbreviates counts as found (`own`; "IDP"). `_decide` passes `(name, jurisdiction)`.

**Result:** the real API matches the simulation.
- **Safety set:** staging 38 → 43/59, approved 33 → 38/53. The five changes are exactly the intended ones: three US/UK false matches become no-match, the "UK driving licence" ambiguous case becomes no-match, and "How do I get an IDP?" is now matched.
- **Answer sets:** 0 of 214 cases changed.
- **Identification sets:** population 33 → 35/42, demo services 30 → 31/37, Tamil 30 → 31/36, multi-need 11/14 unchanged.
- **Follow-ups (17/17) and the 42-question probe:** identical.
- **"I live in the UK. How do I register as an overseas voter?"** is lost on the whole message but rescued by need extraction in the real API (it passes in the safety set).

**Still matched:** "marriage certificate" ×2 → page 17, and "change the name on my PAN card" → Link PAN with Aadhaar. All three answers abstain, but the card is shown. P1-4 (no card on an abstaining, unnamed match) is a UX decision for the owner. The page-17 rename makes its card far less misleading.

## P1-1 — Claim verification

**Investigation:** `p1_1_verification/replay_rules.py` replayed candidate rules on every claim the P0-2 code verified: 239 on staging and 202 on approved (main, held-out and safety sets, `--claims`).

| Rule | Rejected | Wrong claims among them | Correct claims lost |
|---|---|---|---|
| A quote cut from a Yes/No answer keeps that word | 0 | — | 0 |
| **A bare "Yes"/"No" only directly under its question** | 1 | **1**: approved "Apprentices can become EPF members." ← `Yes` (its FAQ question was lost) | 0 |
| A claim keeps every period of the quoted *sentence* | 6 | 0 | **6** (page 30's run-on sentence holds the 14-day and 45-day cases; the voter list; a list item attributed to an earlier paragraph) |
| **A claim keeps every period of its *quote*, adds none from outside its sentence, same units** | 0 | — | 0 |
| **Fee service ("test", "duplicate", "renew") from the row or the heading directly above** | 1 | **1**: "fitness test fee … Two Hundred" ← the certificate-of-fitness row | 0 |

**Design point found in testing:** `_section_heading` returns the *nearest* heading above. For page 39 row 11 (certificate of fitness), that is item 10's "Conducting test of a vehicle …:" header, which would have let the wrong claim through. The fee-service rule therefore uses only the heading directly above the row.

**Changes (`rag.py`):**
- `PERIOD` / `_periods`;
- `YES_NO`;
- `FEE_SERVICES` / `_services`;
- three conditions in `verify_claims`. The row index is computed once, so the heading directly above (`lead`) and the question above a bare answer can be checked.

**Tests:**
- three new unit tests: periods and units; Yes/No; fee service.
- **One test changed deliberately:** "Driving a transport vehicle needs a licence." citing the twenty-years sentence is now rejected (it drops its own quote's age).

**Result:**
- **Answer sets:** identical case by case, including every claim's text, on both databases.
- **Fitness-test question:** now abstains instead of giving the certificate fee (safety set and probe).
- **EPF apprentice question on approved data:** now abstains instead of the wrong "can become".

**Known gap:** a quote cut short before its condition ("may use the vehicle for three months" without "within thirty days") is still accepted when the claim matches the cut quote. The meaning check remains the only guard there.

## P1-2 — Abbreviations
- **Fixed:** in `abbreviates`, a code word ("REV-101") gives no initial in either mode, so "RC" no longer abbreviates "REV-101 Community Certificate". In the non-own mode, that could send an RC question to page 17 whenever page 17 was the only nearby page with those initials.
  - **Measured:** 0 of 73 (approved) and 71 (staging) labelled abbreviation questions change (`p1_2_abbreviations/`).
- **Not changed, on evidence:**
  - **The PAN override:** without it, "change the name on my PAN card" goes to e-Filing registration instead, an equally wrong page.
  - **Spelling out DL/RC:** W11 option C measured a wrong page and a needless choice.
  - **PF/EPS:** correct.
  - **W2:** stays withdrawn.

## P1-3 — Chunking (investigated; change held for the owner)
- **The problem exists:**
  - 4 paragraphs exceed `CHUNK_SIZE` and are cut mid-phrase: page 15 "Passport Seva Online | Portal"; page 19's 2,422-character paragraph; page 30 "Central Motor | Vehicle Rules"; staging page 40, the APY contribution sentence.
  - A quote spanning a cut cannot be verified.
- **No evaluation failure traces to them.**
- **A minimal variant** (2 lines in `chunk_text`): cut after the last sentence end in the second half of the limit, else at a space as today.
  - It makes 3 of the 4 sentences quotable whole (pages 15, 19, 40); chunk counts are unchanged (`p1_3_chunking/sentence_split.*`).
  - Page 30 has no sentence end in range.
- **Held:** it changes stored chunks, so it needs re-embedding. Page 15, otherwise untouched by the migration, would also need re-approval. Applying the code alone would make the stored chunks disagree with `chunk_text`, so it is offered as an option to bundle with the migration (§G).

## P3 — Operational reliability
- **Logging (`main.py`):**
  - one line per request (id, method, path, status, duration), with the id returned as `X-Request-ID`;
  - one line per model call (`extractor.ollama_post`), with duration and outcome;
  - question text, source text and credentials are never logged (tested).
  - Uses the standard library only.
- **Retry:**
  - one retry for a dropped connection, a 5xx, or (embeddings) a 400, the transient error seen twice in 16,859 calls;
  - a timeout is never retried; a 4xx is not retried for generation.
  - Tested. The final suite logged its model calls with no failures and no retries.
- **Frontend:**
  - requests time out after 3 minutes with a clear message (a guidance request can chain several 60 s model calls; the measured maximum is 56 s);
  - a network failure says the server cannot be reached; the admin page no longer shows a signed-out login screen when the backend is down (`14` §14.10).
- **Not changed (documented):**
  - **Session held during model calls:** citizen routes keep a database session open (pool: 5 + 10 overflow). Under about 15 or more concurrent requests, extra requests would wait up to 30 s, then fail. Not observed with one user; fix before multi-user use.
  - **Tamil/voice:** real-speech accuracy is still untested (synthetic voices only); normalisation variance is unchanged.

## Security
- **Ingestion allow-list:** `scraper.require_official` checks the submitted URL and the final URL after redirects.
  - Default domains: `gov.in`, `nic.in`, `pfrda.org.in`; configurable via `OFFICIAL_SOURCE_DOMAINS`.
  - Browser sub-resources (CDNs) are only safety-checked.
  - The README already promised official pages only; this enforces it.
- **DNS rebinding:** the address actually connected to is checked before the page is read, for static fetches (`network_stream` `server_addr`, verified live: `103.195.218.37`) and for the rendered page itself (Playwright `server_addr()`, unit-tested only). A rendered page's scripts and styles keep the pre-request check only.
- **Login:** 5 failed sign-ins per client address per 15 minutes, then 429. A success clears the count. It is held in memory, so behind a proxy uvicorn needs `--proxy-headers`.
- **Tokens:** byte comparison, so a non-ASCII cookie or provenance token gives 401/422, not 500.
- **Assessed, unchanged:**
  - CSRF: SameSite=strict cookie plus CORS restricted to `FRONTEND_ORIGIN` with JSON-only headers;
  - IPv4/IPv6: `_is_public_address` handles IPv6 and IPv4-mapped addresses;
  - secrets: only in `.env`, never logged;
  - DB access: citizen routes use read-only transactions.
- **Remaining (deployment):**
  - HTTPS and `COOKIE_SECURE=true`;
  - session revocation (needs server-side state);
  - rate limits for citizen endpoints (best at the reverse proxy);
  - reproducible installs (`run.sh` reinstalls packages; no lockfiles);
  - process supervision.

## C. Changed files

**Backend:**

| File | Why |
|---|---|
| `backend/procedure_search.py` | P0-2: `COUNTRY_CODE`, `mentions(…, own)`, `_decide` passes the page's name and jurisdiction. P1-2: code words give no initial in `abbreviates`. |
| `backend/rag.py` | P1-1: period, Yes/No and fee-service rules in `verify_claims`. P3: `embed_texts` uses `ollama_post`. |
| `backend/extractor.py` | P3: `ollama_post` (logging and one bounded retry); `call_qwen` uses it |
| `backend/main.py` | P3: request logging with a request ID |
| `backend/scraper.py` | Security: `require_official`, connected-address check (static and rendered) |
| `backend/auth.py`, `backend/routes.py` | Security: login limit (429); byte comparison of tokens |
| `backend/config.py` | `OFFICIAL_SOURCE_DOMAINS` (optional; has a default) |

**Frontend, tests and scripts:**

| File | Why |
|---|---|
| `frontend/src/api.ts`, `App.tsx` (+ their tests) | P3: request timeout; an unreachable server is not shown as signed out |
| `tests/test_identify.py`, `test_guidance.py`, `test_rag.py`, `test_extractor.py`, `test_health.py`, `test_auth.py`, `test_scraper.py` | Tests for each change. One expectation changed deliberately (`test_guidance`, transport-vehicle claim). `ScrapeUrlTest` URLs moved from `example.gov` to `example.gov.in`, as the allow-list requires. |
| `scripts/evaluate_answers.py` | P0-1: additive keys `forbidden`, `card`, `requires`; identification count; `--claims` |
| `fixtures/evaluation/safety.json` (new) | P0-1 |

**Documentation:**

| File | Why |
|---|---|
| `README.md`, `.env.example` | Limitations updated; the optional setting documented (`.env` untouched) |
| Handoff | `19` (new); `00`, `03`, `04`, `05`, `07`, `10`, `11` updated; `16` corrected (dates; PAN wording) |
| Evidence scripts | `run_suite.sh`, `make_snapshot.sh`, `snapshot_run.py`, `validate_migration.py`, `cmp_eval.py`, plus the investigation scripts |

## D. LOC and complexity
- **Tracked files, this session:** about +485 / −54 lines. Of that, backend is +192 / −34; the rest is mostly tests (about 60% of the non-backend lines), frontend and the evaluator.
- **New files in the application:** none. The fixture `safety.json` is new.
- **New dependencies:** none. Logging uses the standard library.
- **New abstractions:** one helper, `extractor.ollama_post`. It replaced two copies of the Ollama POST and error handling, so model-call code is now in one place.
- **Complexity:** `verify_claims` has 3 more conditions, each one line with a comment; `mentions` gained a local `found`.
- The evidence and evaluation scripts are tooling, not application code.

## Final results (code: all changes; snapshot hashes in `master_final/frozen_inputs.txt`)

| Evaluation | Baseline (today, before changes) | Final | Change |
|---|---|---|---|
| Staging main | 75/80 | 75/80 | 0 of 80 cases changed (claims identical) |
| Staging held-out | 23/27 | 23/27 | 0 of 27 |
| Approved main | 74/80 | 74/80 | 0 of 80 |
| Approved held-out | 24/27 | 24/27 | 0 of 27 |
| Multi-need | 11/14 | 11/14 | — |
| Population | 33/42 | **35/42** | US passport and UK licence now unmatched |
| Demo services | 30/37 | **31/37** | UK driving licence now unmatched |
| Tamil | 30/36 | **31/36** | "IDP" (abroad) now matched |
| Follow-up scenarios | 17/17 | 17/17 | Identical |
| Audit probe (42) | — | — | Identical except the fitness test: misattributed fee → abstains |
| **Safety set, staging** | 38/59 | **43/59** | Incorrect or misleading 2 → **1**: the page 17 card (the income answer under it is correct). Confident wrong pages 8 → **5**. |
| **Safety set, approved** | 33/53 (+6 skipped) | **38/53** | Incorrect or misleading 3 → **2**: the income and nativity lists, both wrong answers; the page 17 card is shown with them. Confident wrong pages 7 → **4**. |

**Correction (26 Oct):** the first version of this table gave approved's two failures as "page 17 card; nativity list".
- The evaluator checked the card before the claims, so the wrong income-certificate claim was reported only as a misleading card.
- The evaluator now reports a forbidden claim first and notes the card with it (`scripts/evaluate_answers.py`; re-run `evidence/evaluations/premigration_safety/`, claims identical).
- The counts are unchanged; the labels are now right.

**The separate measures the brief asks for:**

| Measure | Staging (main + held-out + safety) | Approved (main + held-out + safety) |
|---|---|---|
| 1. Correct identification | 149 of 166 | 145 of 160 |
| 2. Incorrect confident identification | 6: marriage ×2, PAN name, Dubai → Register to Vote; plus the tie-rule grace-period case in held-out and one page-39 fallback | 4: marriage ×2, PAN name, Dubai |
| 3. Correct abstention or no match | 21 (8 + 3 + 10) | 21 |
| 4. Incorrect abstention (identification misses, missed answers) | 4 misses + 5 missed answers | 4 misses + 5 missed answers |
| 5–6. Retrieval | No case is lost because evidence was stored but not retrieved | Same |
| 7. Correct answers | 117 (incl. 20 flagged partial) | 112 (incl. 21 flagged partial) |
| 8. Unsupported answers | 0 | 0 |
| 9. Incorrect answers | 0 wrong claims; 1 misleading card (page 17) | 2: the income and nativity lists (data), both under the page 17 card |
| 10. Citation correctness | No claim cites another page's passage; every quote verified verbatim | Same |
| 11. Completeness | 2 incomplete in the safety set | 2 incomplete in the safety set |

**Notes on the measures:**
- "Correct identification" counts the evaluator's identification line (correct, or correctly unmatched).
- "Incorrect answers" counts `forbidden` hits and unsupported claims.
- **Latency:** median 4–6 s, maximum 55 s.
- The evaluator's outcome "retrieval failure" also counts identification-stage failures. Measures 5–6 use the stage instead: no case failed at the retrieval stage (evidence stored but not retrieved).

## E. Test results
| Check | Before | After | Run |
|---|---|---|---|
| Backend unit tests | 221 OK | **237 OK** | Yes (`REQUIRE_DB_TESTS=1 … discover -s tests`) |
| Frontend tests | 63 passed | **65 passed** | Yes |
| TypeScript + unused-code check | OK | OK | Yes |
| Frontend build | OK | OK | Yes |
| Evaluation suite (12 runs incl. safety) | Baseline reproduced | See "Final results" | Yes |
| Live scraper check (allow-list, connected address) | — | OK | Yes |

**Not run:**
- live outage drills (PostgreSQL or Ollama stopped);
- real-speech voice tests;
- concurrent-load tests;
- a browser session against the running app.

## F. Safety verification
- **`.env`:** unchanged (last modified 15 Oct 08:38:46). No value was printed; snapshot runs load it into process memory only.
- **No secrets** in logs, reports or output.
- **No database writes:** both databases have identical checksums before and after every suite. Approved: `016980ee…` / `3e45c78f…`, 24 pages, 122 chunks. Staging: `8aba737f…` / `93000b69…`, 26 pages, 140 chunks.
- **No migration, no re-embedding, no staging-to-approved import.**
- **No destructive Git operation, no staging of files, no commit, no push.** HEAD is still `3491415`. The uncommitted work from before this session is preserved; the new files are listed in §C.
- **The approval workflow is unchanged** (verified in code). The threshold stays at 0.53 (checked effective). W2 stays withdrawn. H1, W1, W3, W10 and H3 are intact; their tests pass and their cases are unchanged.

## G. Operations needing the owner's approval
1. **The approved-database migration** (`07`, "Proposed migration"; pre-check passed today).
   - **Purpose:** fix the live wrong answers (TN income and nativity lists) and page 17's misleading card, add pages 39 and 40, and recover the lost FAQ questions.
   - **Records affected:** 13 existing pages moved or re-approved (9 re-approved at the same URL: 17–20, 27, 35–38; 4 moved: 16, 31–33), 2 added (39, 40), 11 untouched.
   - **Result:** 26 pages and 140 chunks, as staging (about 140 if a live page changes first).
   - **How:** admin workflow only, with `07`'s "Reviewed card values" applied and every other card kept.
   - **Risks:** a minutes-long gap per re-approved page; reviewer error.
   - **Validation:** `validate_migration.py --embeddings` (0 failed checks expected), then the suite. Expected: the staging results above (`premigration_safety/staging_safety.txt` for the safety set).
   - **Rollback:** restore the step-0 dump (`07`).
2. **Optional, with the migration: sentence-aware chunk splitting** (P1-3).
   - **Affects:** pages 15, 19 and 40, re-embedded (page 15 needs re-approval).
   - **Risk:** retrieval changes on those pages; measure on staging first, which needs approval to write staging.
3. **P1-4 (UX decision):** hide the procedure card when an answer abstains and the question does not name the procedure (the marriage and PAN cases). Frontend only.
4. **The two safety cases marked `review`:** confirm that "marriage certificate" is out of scope.
5. **Deployment decisions** (§H): hosting, HTTPS, proxy and process supervisor.
6. **Committing this work.**

## H. Production readiness
| Area | Assessment |
|---|---|
| 1. Functional correctness | Good on the measured sets: 75/80, 23/27, 74/80, 24/27, with 0 unsupported claims. Wrong answers remain only where the stored data is defective. |
| 2. RAG reliability | Good. Retrieval loses nothing measured; verification now also checks periods, Yes/No context and fee service. The meaning of a cut quote is still checked only by the model. |
| 3. Source data quality | **Not ready on the approved database:** 2 wrong document lists, lost FAQ questions, page 17's card. Ready once the reviewed migration is run. Official-page defects are listed. |
| 4. Identification safety | Improved: confident out-of-scope matches 6 → 3. The 3 that remain abstain, but show a card. No general intent or jurisdiction model (documented). |
| 5. Answer verification | Strong for the measured error classes (each has a rule and tests); the meaning check remains a model. |
| 6. Security | Code-level items done. **Not ready:** HTTPS, session revocation, citizen-endpoint rate limits and reproducible installs are deployment work. |
| 7. Operational reliability | Logging and bounded retries are now in. Database-session pressure under concurrency is untested; there are no outage drills. |
| 8. Deployment readiness | **Not ready:** no deployment artefacts (HTTPS, supervisor, backups schedule, monitoring). |

## Progress log
| Time | Step | Result |
|---|---|---|
| 17:35 | Reconnaissance: Git state, handoff, code (procedure_search, rag, routes, scraper, auth, config, extractor, database, main, api.ts) | State as recorded in `18`; 23 frozen-input hashes identical to the final-code run |
| 17:38 | Unit baseline | Backend 221 OK; frontend 63 passed; tsc + unused-code check OK; build OK |
| 17:40 | Full evaluation baseline started (`master_baseline/`) | — |
| 17:53 | P0-1: `fixtures/evaluation/safety.json` (59 cases) and additive evaluator keys (`forbidden`, `card`, `requires`, identification summary, `--claims`) | — |
| 18:00 | P0-3: pre-migration re-scrape of all 26 staging URLs with today's scraper | **No live drift**: the 15 pages to be (re-)approved equal their staging text exactly; the 9 kept pages differ only by the "View PDF" / "Jansuraksha Scheme" labels `07` predicted |
| 18:05 | P0-3: `validate_migration.py` (read-only) | Staging passes every check except the 3 outstanding reviewer corrections (page 17 name and summary, page 40 eligibility) |
| 18:07 | Baseline, staging part: 8 runs compared with the final-code runs (`h3_fix/`) | **All 8 identical** apart from timings (temperature 0 reproduces every answer) |
| 18:08 | P1-3: in-memory simulation of a sentence-aware cut (`p1_3_chunking/`) | 4 over-long paragraphs; the cut makes 3 sentences quotable whole (pages 15, 19, 40); no observed failure; needs re-embedding, so it is held for the migration decision |
| 18:21–19:23 | Safety set on the baseline snapshot; full suite on the P0-2 snapshot | P0-2: +5 safety cases on each database; answer sets 0 changed; 3 identification sets improved |
| 19:2x | P1-1 replay on 441 verified claims | Bare Yes/No and fee service: 1 wrong claim each, 0 correct lost; sentence-level periods: 6 correct lost, so the quote-level rule was used |
| — | P1-2 measurement (144 questions) | Code-word initials: 0 decisions change |
| — | P3 and security code with tests | Backend 237 OK; frontend 65 |
| 21:40–22:30 | Full suite on the final snapshot | See "Final results"; checksums unchanged |
| 26 Oct 00:0x | Pre-migration verification: certificate traces on both databases | Approved income and nativity answers are wrong (data); staging correct; card shown in all four |
| 26 Oct 00:1x | Evaluator: a forbidden claim reported before a misleading card; safety re-run (`premigration_safety/`) | Labels corrected; counts and claims unchanged; checksums unchanged |
| 26 Oct 00:1x | Validator revised; self-test; approved pre-migration run | Correct migration passes (0 failures); 11 of 11 faults caught; approved: 30 expected failures; staging refused |
| 26 Oct 00:3x | `07` and `19` reconciled (counts, page 17 name, reviewed values, baselines) | — |
