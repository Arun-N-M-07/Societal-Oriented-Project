# 07 — Database, safety and migration plan

## Update 28 Oct 2026, 09:35: three delegated candidates approved
- **N3** Police Clearance Certificate, **N4** Aadhaar Enrolment and **N8** Registration of Births and Deaths were approved through the admin routes into staging and the approved database. N1 and N10 are deferred (`evidence/investigations/p9_final/candidate_review_27oct.md`).
- **Approved:** 27 pages / 134 chunks, `750d4dc2f448e94373f8eb509b339fe2` / `e7fee54863a0304e9455ce09edaf4a69` (ids 39–41 are the new pages).
- **Staging:** 28 / 146, `c442a59cbdfbd0af9c49c9a7eb542372` / `290cf4965b0fd93d6f43c472012d151d` (ids 41–43).
- **Unrelated rows:** byte-identical in both.
- **After the migration:** **28 pages / 146 chunks** (verified: that is staging now).
- **The table below is the state before these approvals.**

## Current state (VERIFIED 27 Oct 2026, 18:52 IST)
**Read this before the older sections below.** Since the text below was written, two owner decisions have changed the plan:
- **Page 17 is deleted, not replaced.** This is the e-Sevai FAQ, "REV-101 Community Certificate", `https://tnesevai.tn.gov.in/Citizen/FAQ.html`.
- **Five candidates were delegated to Claude:** N1, N3, N4, N8 and N10. Their review is in `evidence/investigations/p9_final/candidate_review_27oct.md`.

The exact operator checklist is **`19`, "Final migration approval checklist"**, revised 27 Oct. Its record-level plan is summarised here.

| Database | Role | Pages | Chunks | md5 procedures / chunks |
|---|---|---|---|---|
| `procedureassist` | **Approved; citizens see it.** Unchanged since 23 Oct | 24 | 122 | `016980eee56654079df99cddfbabaf00` / `3e45c78f7b85623ad6d9468fa9b34171` |
| `procedureassist_staging` | Migration rehearsal and the validator's reference. **Page 17 deleted 27 Oct 10:50** through `DELETE /api/admin/procedures/17` (in-process, `evidence/investigations/p9_final/admin_workflow.py`) | 25 | 134 | `96697b50b666c5937d9e6bc10186123e` / `73da35b39dc3956bbaed33125ef6f6ca` |
| `procedureassist_scratch` | **New 27 Oct 10:47:** a restore of the approved database, for testing candidates on a production copy. May be dropped when no longer needed | 24 | 122 | equal to approved |
| `procedureassist_test` | Unit tests; empty between runs | 0 | 0 | — |
| `procedureassist_db` | Not part of this project; never touched | — | — | — |

**Checks.** All four project databases have 0 orphan chunks, embeddings of 1024 dimensions, and no chunk-index gaps (`evidence/database/db_checksums.sql`).

**Schema facts that make the deletion safe (VERIFIED):**
- The only foreign key is `procedure_chunks.procedure_id` → `procedures.id ON DELETE CASCADE`.
- Nothing else stores a procedure id.
- **The page 17 deletion test:** on the scratch copy, through the real route, in a rolled-back transaction. It removed exactly page 17 and its 4 chunks (ids 33–36): 24 → 23 pages, 122 → 118 chunks. Every other procedure and chunk was byte-identical before and after (`evidence/investigations/p9_final/page17_deletion_test_scratch.txt`).

**Backups** (`/Users/arunnm/Projects/SOP-backups/`, custom format; outside the repository; never commit them):

| File | Source | Bytes | SHA-256 |
|---|---|---|---|
| `procedureassist_2026-10-23_before_source_cleanup.dump` | approved, 23 Oct | 700,813 | `4e22ba1f5b5bb67c0ae5f3e25007583d6da8353f06530f12ef1ae75bbde42a04` |
| `procedureassist_2026-10-27_dry_run.dump` | approved, 27 Oct 02:55 (restore proven) | 700,813 | `a20557ddb4903c1afb3796bbb481696bf587190e50309d2d5fdd9ec063911196` |
| `procedureassist_2026-10-27_before_candidates.dump` | approved, 27 Oct 10:46 (restored into the scratch database; checksums equal) | 700,813 | `20b54b9e1d7fc2af69673bad33c3f0cb85ccba84245978fb69315d22c4dc437d` |
| `procedureassist_staging_2026-10-27_before_page17_deletion.dump` | staging, 27 Oct 10:46 (26 pages / 140 chunks) | 800,209 | `9616f56c2f666e8d87950328e200ecbb5aa7e237b01cd2ad8617056da332e9b1` |

**None of these replaces the fresh backup** required immediately before the production migration (`19`, item 5).

**The revised migration (NOT executed; REQUIRES OWNER APPROVAL):**

| Action | Approved ids | Chunks |
|---|---|---|
| **Delete** | 17 | its 4 chunks go by cascade |
| **Replace** (delete, then re-approve the same URL with the re-scraped text) | 18, 19, 20, 27, 35, 36, 37, 38 | |
| **Move** (approve the `?mobile-app=1` URL, then delete the old record) | 16, 31, 32, 33 | |
| **Add** | 39 (Vehicle Registration Fees and User Charges), 40 (APY, PFRDA) | |
| **Untouched** | 15, 21, 22, 23, 24, 25, 26, 28, 29, 30, 34 | 32 chunks, embeddings unchanged |

- **Expected result:** **25 pages / 134 chunks**, equal to staging today, if no live page changes before the migration.
- **Delegated candidates (28 Oct):** N3, N4 and N8 were approved first (5 + 5 + 2 = 12 chunks), giving **27 / 134 before the migration and 28 / 146 after it** (verified; see the update above).
- **Page 39's card step** (owner decision 27 Oct): "Refer to the fee table to identify the applicable fee for the relevant vehicle-related service."

## Databases on this machine (as written 23 Oct; see "Current state" above for today)
| Database | Purpose | State (23 Oct 2026) |
|---|---|---|
| `procedureassist` | **Approved** data that citizens see; the app's `DATABASE_URL` | 24 pages, 122 chunks. **Unchanged** since the audit began. |
| `procedureassist_staging` | Rehearsal copy with the proposed cleanup | 26 pages, 140 chunks. Never read by the running app. |
| `procedureassist_test` | Automated tests (name must end in `_test`) | Rebuilt by tests |
| `procedureassist_db` | Empty, unused (no tables) | — |

## The staging database: complete record

### Why it was created
- **The trigger.** On 23 Oct 2026 the source audit (`06`) found that 9 approved pages had lost or polluted meaningful text at scraping time (FAQ questions, eligibility cards, fee-table rows, menus, galleries). Two official sources were also missing (the Rule 81 fee table and PFRDA's APY page).
- **Why not fix in place.** Fixing this means deleting and re-approving citizen-facing records. Doing that blind could leave procedures without evidence or introduce new errors.
- **What it allowed.** A full copy was used to apply every proposed change and evaluate it with the real models *before* asking the owner to approve anything in `procedureassist`.

### How it was separated from the approved database   
      - **Created** at about 21:23 IST on 23 Oct 2026, with `createdb procedureassist_staging` and then `pg_dump procedureassist | psql -d procedureassist_staging`.
  - It started as an exact copy: 24 pages, 122 chunks.
  - It is a separate PostgreSQL database on the same server. The app never reads it; `.env` still points at `procedureassist`.
- **Pointing scripts at it.** Every script that wrote to staging took `DATABASE_URL` from the environment (the same server URL with the database name replaced) and **asserted** that it ended in `/procedureassist_staging` before writing. `.env` was never edited.
- **Backup first.** A custom-format dump of the approved database was taken at the same time; see "Backup and restore".
- **Verified afterwards.** Through the session the approved database was repeatedly checked against the backup checksums (latest 23:55 IST, `evidence/database/checksums_procedureassist.txt`), and it always matched. The 21:43 restore test (into a scratch database, then dropped) proved the dump restores to identical content.

### How it was built (sequence; scripts in `evidence/other/scripts/`)
1. **Dry-run re-scrape** (`rescrape_dry.py`). All 24 URLs plus the Rule 81 page were re-scraped with the fixed scraper. Nothing was written; the per-page diff is in `evidence/source_audits/rescrape_dry_run_diff.json`.
2. **Mobile view** of the income-tax manuals (31, 32, 33): `?mobile-app=1` was verified to give the same paragraphs without menus.
3. **`apply_staging.py`** (staging only, one transaction):
   - replaced `source_text` and rebuilt chunks for 17, 18, 19, 20, 27, 35, 36, 37, 38 (dry-run text);
   - changed the URL and text of 31, 32, 33 to `?mobile-app=1`, and only the URL of 16;
   - added the Rule 81 page as a new record (ID 39). Its name, department and steps were drafted by `extract_procedure`.
4. **Manual values, not reviewer-approved.** The staging name of 39 ("Vehicle Registration Fees and User Charges") and its department were set by SQL to match page 27's department.
5. **PFRDA page added** (ID 40): text from a verified fetch, draft by `extract_procedure`, name set to "Atal Pension Yojana (PFRDA scheme details)".
6. **Chunker iterations, all re-indexed on staging only:**
   - a loose heading rule;
   - a tightened rule (lines ending in "?" or ":");
   - a heading-repeat experiment (rejected);
   - a return to the final rule.

   Before the evaluations, every staging page's chunks were checked to equal `chunk_text(source_text)` under the final chunker.
7. **Page 39 re-scraped again** by the other Claude session with the fee sub-row fix (`_row_context`), giving 12 chunks. Final state: **26 pages, 140 chunks**, chunks md5 `93000b69…`. This is the snapshot every staging evaluation used; see `05`.

**Important:** staging changes were made by scripts, **not** through the admin review workflow. No human has reviewed the staging text, names or steps. The page 17 record in staging still carries the wrong name ("REV-101 Community Certificate") and its CAN-editing steps. That is why the real migration must go through Extract → review → Approve.

### Where each staging page's text came from (verified 24 Oct 2026)
Each staging page's `source_text` was compared with the saved scrape files, now copied to `evidence/source_audits/staging_inputs/` (SHA-256 in `SHA256SUMS.txt`; the originals were in a temporary folder).

| Staging pages | Text is exactly | Scraper version |
|---|---|---|
| 17, 18, 19, 20, 27, 35, 36, 37, 38 (re-scraped) | `dry.json` (dry-run re-scrape, 21:22) | Scraper of 21:21: div/span/summary text and one paragraph per table row, **before `_row_context`** |
| 15, 16, 21 (kept; 16 only its URL changed) | `dry.json`, which for these equals the approved text | — |
| 31, 32, 33 (moved) | `mobile.json` (`?mobile-app=1` fetch, 21:23) | Scraper of 21:21 |
| 22, 23, 24, 25, 26, 28, 29, 30, 34 (kept) | The approved text, unchanged | The original scraper |
| 39 (added, Rule 81 fees) | `final_rescrape.json` (22:01); also equal to today's `clean_html(fees39.html)` | Final scraper (with `_row_context`) |
| 40 (added, PFRDA APY) | The PFRDA entry in `apy_candidates.json` (21:57) | Scraper of 21:57 |

Two consequences for the migration:
- **The kept pages were deliberately not re-scraped.** Today's scraper adds only noise to them: one "View PDF" button label on each of the eight Parivahan pages (22–26, 28–30), and the labels "Atal Pension Yojana" and "Jansuraksha Scheme" on page 34 (`final_rescrape.json` vs the approved text). Re-approving them would change their chunks for no benefit. Leave them alone.
- **Re-approval uses today's scraper, not the 21:21 one.** The texts of the 9 re-scraped and 3 moved pages that were evaluated on staging came from the earlier scraper. If `_row_context` (or a live page edit) changes a page, the migrated text will differ from what was evaluated. See "Pre-migration check" below.

The scripts that re-indexed staging during the chunker iterations, added page 40 and re-scraped page 39 were not preserved; only their outputs and the final state are. The final state was checked chunk by chunk against `chunk_text(source_text)` before the evaluations.

### How 24 pages / 122 chunks become 26 pages / 140 chunks
| Group | Pages | Chunks approved → staging |
|---|---|---|
| Kept (identical text **and** chunks) | 15, 21, 22, 23, 24, 25, 26, 28, 29, 30, 34 | 7+5+2+2+1+1+1+2+2+7+2 = **32 → 32** |
| Re-scraped, same URL | 17, 18, 19, 20, 27, 35, 36, 37, 38 | 4+10+4+6+2+3+5+4+3 = **41 → 45** (17: 4→6, 18: 10→11, 19: 4→3, 20: 6→6, 27: 2→2, 35: 3→3, 36: 5→5, 37: 4→5, 38: 3→4) |
| Replaced URL (`?mobile-app=1`) | 16, 31, 32, 33 | 18+9+5+17 = **49 → 47** (16: 18→19, the same text re-chunked by the final chunker; 31: 9→8; 32: 5→3; 33: 17→17) |
| Removed | none | 0 |
| Added | 39 (Rule 81 fees), 40 (PFRDA APY) | **0 → 16** (12 + 4) |
| **Total** | **24 → 26** | **122 → 140** (32 + 45 + 47 + 16) |

- **Re-chunked only:** no page in the plan needs re-chunking without a text change. The 11 kept pages already chunk identically under the final chunker. Page 16's chunk change comes with its URL move.
- **Record IDs.** Staging kept the original IDs for changed pages and used 39 and 40 for the new ones. The real migration through the admin workflow will create **new** IDs for every re-scraped, moved or added page. Nothing outside the database stores IDs, so this is harmless; evaluation fixtures match by URL.
- **Per-page counts:** `evidence/database/approved_pages.txt` and `staging_pages.txt`.

### What staging improves, what it regresses, what stays open
**Improvements (evidence: `05`, `evidence/traces/targeted_*.txt`):**
- **Wrong answers fixed.** Approved data gives "Apprentices can become EPF members" (wrong) and Tamil Nadu income-certificate items from another list (wrong). Staging gives "cannot" and the correct 9-item list.
  - **26 Oct:** the approved nativity-certificate answer also mixes in other certificates' items (Community Certificate of Father…, Income Tax Return, Proof of Income), while staging gives the correct 5 items (`p0_3_premigration/certificate_trace_*`).
  - Since 25 Oct the apprentice answer is blocked in code (it now abstains); the income and nativity lists can only be fixed by the migration.
- **Questions newly answered:** the EPF age group (18–54), "Can an income-tax payer join APY?" (PFRDA), the held-out appeal fee (row-level fees), mixed-language Aadhaar documents (partial), and the EPS government contribution.
- **Best score.** Final code + H1 on staging is the best combination measured: 75/80 (54 complete), 23/27, 0 incorrect (24 Oct; `05`, "H1 fix runs").
  - Historical result, final code before H1: 74/80 (52 complete), 23/27, 0 incorrect.

**Regressions and new costs:**
- **Held-out grace-period fee.** It is sent to the renewal page by the tie rule, then abstains (the model omits Rs. 1,000/yr, which is correctly rejected).
- **"I just turned 18" asks to choose** between How to Vote and Register to Vote. On approved data it is answered.
- **Held-out Tamil voter-helpline number:** a missed answer (generation).
- **Identification set "population":** 34 → 33.

**Unresolved on staging:**
- APY pension slabs abstain (H2);
- motorcycle RC renewal abstains, because the right row is not retrieved (H3);
- the document-kind false rejection (H1);
- the page 17 name and steps need reviewer correction;
- source gaps (`06`).

## Integrity checks (all passed on 23 Oct 2026)
- **No unintended writes.** The approved database equals its backup:
  - procedures md5 `016980eee56654079df99cddfbabaf00`;
  - chunks md5 `3e45c78f7b85623ad6d9468fa9b34171`;
  - 24 pages, 122 chunks.
  - Checksum queries: `evidence/database/db_checksums.sql`.
- **Consistency, both databases:** 0 orphan chunks, every embedding has 1024 dimensions, and every page's `chunk_index` runs 0..n-1 without gaps.
- **Embeddings are current.**
  - Every approved chunk's stored embedding had cosine 1.0000 with a fresh embedding of its text.
  - Every approved chunk equals `chunk_text(source_text)` under the chunker of that time.
- **Staging isolation.** Staging is a separate database created with `createdb` + `pg_dump | psql`. Every staging write was made by a script that asserts its `DATABASE_URL` ends in `/procedureassist_staging`.
- **Rechecked 24 Oct 2026, 00:25 IST,** after the final staging evaluations ended (00:01–00:06):
  - both databases still give exactly the checksums above;
  - the backup's SHA-256 still matches;
  - in the 11 kept pages, text and chunk contents are identical between the two databases;
  - page 16 has identical text but different chunks (re-chunked);
  - every other page differs in both.
- **Second checksum formula.** `evidence/evaluations/eight_run_matrix/frozen_inputs_eight_runs.txt` and the other session's notes give procedures md5 `618bb8fb…` (approved) and `6154bf02…` (staging). Those values are `md5(string_agg(id||name||source_url||source_text, '|' order by id))`, which leaves out department, summary and structured data. Both values were reproduced on 24 Oct, so they show the same unchanged data as `db_checksums.sql`. The chunks md5 is the same in both formulas.

## Backup and restore
- **Backup of the approved database**, taken before any staging work: `/Users/arunnm/Projects/SOP-backups/procedureassist_2026-10-23_before_source_cleanup.dump`.
  - PostgreSQL custom format; SHA-256 `4e22ba1f5b5bb67c0ae5f3e25007583d6da8353f06530f12ef1ae75bbde42a04`.
  - It contains only `procedures` and `procedure_chunks`: public official page text, no credentials.
  - It is outside the repository on purpose. Do not commit dumps.
- **Verify a dump:**
  ```bash
  pg_restore -l <dump>
  ```
- **Restore** (stop the backend first). Each command in turn:
  ```bash
  dropdb procedureassist
  ```
  ```bash
  createdb procedureassist
  ```
  ```bash
  psql -d procedureassist -c "CREATE EXTENSION IF NOT EXISTS vector"
  ```
  ```bash
  pg_restore -d procedureassist <dump>
  ```
  Then re-run the checksum queries.
- **Take a fresh backup** immediately before any approved migration:
  ```bash
  pg_dump -Fc procedureassist -f ../SOP-backups/procedureassist_<date>_before_migration.dump
  ```
- **Dry run of this procedure, 27 Oct 2026 (`21`, Phase 8):**
  - Dump `procedureassist_2026-10-27_dry_run.dump`: 700,813 bytes, the same size as the 23 Oct dump. SHA-256 `a20557ddb4903c1afb3796bbb481696bf587190e50309d2d5fdd9ec063911196`. `pg_restore -l` lists 35 entries.
  - It was restored into a new scratch database (`procedureassist_restorecheck`) with the sequence above. The copy's checksums equal the approved database's, and every integrity check passes. The scratch database was then dropped (`evidence/database/restore_check_27oct.txt`).
  - **The step-0 fresh backup is still required right before the migration.**
- **Integrity rechecked 27 Oct 2026** (`evidence/database/db_integrity.sql`, `db_integrity_27oct.txt`). Both databases pass:
  - no duplicate URLs, orphaned chunks, missing embeddings or chunk-numbering gaps;
  - all embeddings 1024 dimensions;
  - deleting a procedure cascades to its chunks;
  - the URL is unique.

## Why the approved database has not been migrated
1. **No human has reviewed the staging content.** Scripts wrote it; the project rule is that only the admin's Extract → review → Approve workflow puts a page into the approved database.
2. **Known review corrections are outstanding.** Page 17's name and steps are wrong. The names and departments of 39 and 40 were set by a script or SQL.
3. **The owner has not approved it.** Changing approved records needs the owner's explicit approval of the exact plan. Approving staging, or a good evaluation score, is not that approval.
4. **Staging is not strictly better.** It fixes 2 known wrong answers and gives more complete answers, but it adds a held-out regression and new ties. The owner should weigh these (see above and `05`).

## What the owner's approval must cover
Before anyone changes `procedureassist`, the owner states in writing (a chat message is enough) that they approve:
- the exact page list and actions in the table below;
- the reviewed card values (pages 39 and 40; page 17 is now deleted), and keeping every other card as it is;
- who reviews each page in the admin workflow;
- a window in which citizen answers may be briefly missing or inconsistent (step 4 deletes before it re-approves);
- the rollback: restoring the step-0 dump.

Anything outside that list (another page, a script instead of the workflow, a different order) needs a new approval.

## Update 25 Oct 2026 (master reliability work, `19`)
- **Pre-migration check: done 25 Oct, passed** (`evidence/investigations/p0_3_premigration/rescrape_vs_staging.*`).
  - With today's scraper, the 13 existing pages the plan moves or re-approves, and the 2 new pages, give exactly their staging text.
  - Of the 11 untouched pages, 9 differ only by the label paragraphs predicted below, and 2 (15, 21) are identical.
- **Validation is a read-only script:** `evidence/other/scripts/validate_migration.py` (revised 26 Oct; `--embeddings` also re-embeds and compares).
  - It refuses `procedureassist_staging` as its target, because staging is the reference.
  - It checks counts (26 pages; chunks equal to the reference's 140), text equal to staging, chunks equal to `chunk_text`, contiguous indexes, orphans, and stored and fresh vectors (one per chunk, 1024 finite values, not zero) before any cosine comparison.
  - It checks FAQ question-answer pairs equal to staging's.
  - It checks every card field against "Reviewed card values" below.
  - Evidence: `validate_migration_selftest.py` applies these values to the staging records in memory; a correct migration passes with 0 failures and each of 11 deliberate faults is caught (`p0_3_premigration/validate_selftest.txt`). On the approved database before migration, it lists exactly the pages the migration changes (30 failed checks).
- **Reviewed card values:** see the section below; they are the same values the validator enforces.
- **Final approval checklist** (exact operations, reviewer assignment, unavailability window, backup and rollback, exclusions, the owner's open decisions): `19`, "Final migration approval checklist".
- **Optional, the owner's choice:** sentence-aware splitting of over-long paragraphs (`19`, "P1-3").
  - It changes the chunks of pages 15, 19 and 40, so page 15 (otherwise kept) would also need re-approval.
- **Expected effect:** the staging results with the current code (`19`, "Final results").

## Reviewed card values (the reviewer's corrections; proposals for the owner's approval)
**Rule for every page not listed here:** the card (name, department, jurisdiction, summary, eligibility, steps) stays exactly as it is today.
- In the admin workflow, the reviewer replaces the model's fresh draft with the current values.
- These are in `procedureassist_staging`, and in the approved database until step 4 deletes the record, so copy them first.

**Page 17: SUPERSEDED on 27 Oct 2026.** The owner decided to **delete** page 17 completely, not replace it. **Do not enter these values.** They are kept only as the record of the earlier proposal.

**Page 17, earlier proposal** (`https://tnesevai.tn.gov.in/Citizen/FAQ.html`):
- **department:** unchanged ("Information Technology and Digital Services Department").
- **name:** **e-Sevai FAQ: CAN and certificate documents**. Do not put "Tamil Nadu" in the name: its initials "TN" would make page 17 an abbreviation match for every "TN" question.
- **jurisdiction:** Tamil Nadu.
- **summary:** "Frequently asked questions from the Tamil Nadu e-Sevai portal: what a Citizen Access Number (CAN) is and how to find or edit it, the documents required for community, nativity, income, solvency, no male child, unmarried, inter-caste marriage, widow, OBC and deserted women certificates, and how to check an application's status and find returned applications." (FAQ 1–18)
- **eligibility:** "A Citizen Access Number (CAN) is required to avail e-Sevai services." (FAQ 1–2)
- **steps:** the 11 steps of FAQ 6 ("How do I edit the details of my CAN?"), word for word as on the official page, except the first:
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

**Page 39** (`https://parivahan.gov.in/en/content/fees-and-user-charges`, new):
- **name:** Vehicle Registration Fees and User Charges.
- **department:** Ministry of Road Transport and Highways (Parivahan).
- **jurisdiction:** India.
- **summary:** as drafted in staging.
- **steps:** one step: **"Refer to the fee table to identify the applicable fee for the relevant vehicle-related service."** (owner decision, 27 Oct 2026).
  - It replaces "Find your service in the table and pay the amount listed against it.", which the page does not state.
  - The page is a fee table, not a payment workflow. It does not mention Rule 81, so the card must not either.

**Page 40** (`https://www.pfrda.org.in/schemes/atal-pension-yojana-apy`, new):
- **name, department, jurisdiction, summary and steps:** as drafted in staging (name "Atal Pension Yojana (PFRDA scheme details)", department "Pension Fund Regulatory and Development Authority (PFRDA)"). The steps are supported by the page's "Join APY" section.
- **eligibility:** "All Indian citizens with savings bank accounts in banks or Department of Posts, aged between 18 and 40 years. From 1st October, 2022, any citizen who is or has been an income-tax payer is not eligible to join APY."
  - The page: "any citizen who is or has been an income-tax payer, is not eligible to join APY".

## Proposed migration as of 26 Oct (SUPERSEDED for page 17; NOT executed; needs the owner's explicit approval)
**Revision of 27 Oct.** Page 17 is now **deleted** (no re-approval).
- In step 4 below, page 17 is removed from the list of re-approved pages, and the step-4 review note about page 17 no longer applies.
- The expected totals are 25 pages and 134 chunks.
- The spot-check no longer involves a page 17 card.
- The current checklist is `19`, "Final migration approval checklist", together with "Current state" at the top of this file.

**Pre-migration check (read-only; done 25 Oct and passed, see "Update 25 Oct"; repeat it if the live pages may have changed):**
- Dry-run re-scrape the 13 pages being re-approved (the 9 re-scraped and the 4 moved) with **today's** scraper. Write nothing.
- Compare the output with the staging text, paragraph by paragraph, as `rescrape_dry.py` did.
- If any text differs (because of `_row_context` or a live page edit), check that page's answers on staging again before migrating. Otherwise, the staging evaluation is evidence for exactly the text being approved.
- If any application code has changed since the final-code evaluations (hashes in `evidence/evaluations/master_final/frozen_inputs.txt`), re-run the staging baseline first.

Goal: the approved database ends up equal in content to the validated staging database.
- **Expected result:** 26 pages and about 140 chunks/embeddings. Live pages can change between rehearsal and approval, so the reviewer compares the extracted text with the staging text.
- **How pages go in:** every new or re-scraped page goes through the admin **Extract → review → Approve** workflow, so a human approves the text.
- **Order:** add before delete wherever the URL changes, so no procedure is ever without evidence.

| Step | Pages (approved ID → URL) | Action | Current chunks removed (cascade) | Why |
|---|---|---|---|---|
| 0 | all | Fresh `pg_dump` backup; stop citizen traffic or accept a short window | — | Rollback point |
| 1 | new | **Add** `https://parivahan.gov.in/en/content/fees-and-user-charges` with the reviewed card values above (name "Vehicle Registration Fees and User Charges", department "Ministry of Road Transport and Highways (Parivahan)"). Staging: 12 chunks. | — | Rule 81 fees that pages 28–30 refer to |
| 2 | new | **Add** `https://www.pfrda.org.in/schemes/atal-pension-yojana-apy` with the reviewed card values above (name "Atal Pension Yojana (PFRDA scheme details)", department "Pension Fund Regulatory and Development Authority (PFRDA)", corrected eligibility). Staging: 4 chunks. | — | APY income-tax-payer exclusion, pension slabs, spouse/nominee |
| 3 | 16, 31, 32, 33 | **Approve** the same page at `<url>?mobile-app=1` (for 16, drop `&utm_source=chatgpt.com`), **then delete** the old record | 16: 15–32; 31: 82–90; 32: 91–95; 33: 96–112 | Menu-free official page, nothing lost |
| 4 | 17, 18, 19, 20, 27, 35, 36, 37, 38 | **Delete, then re-approve the same URL** with the fixed scraper (a gap of minutes per page, because the URL is unique) | 17: 33–36; 18: 37–46; 19: 47–50; 20: 51–56; 27: 69–70; 35: 115–117; 36: 118–122; 37: 123–126; 38: 127–129 | Recovered FAQ questions, eligibility cards, row-level fees, sub-row context, GST note; gallery removed |
| 5 | 15, 21, 22, 23, 24, 25, 26, 28, 29, 30, 34 | **No change** | — | Text and chunks are already identical to staging, checked chunk by chunk; the final chunker produces the same chunks |

**Review notes for step 4:**
- ~~Page 17 must be corrected by the reviewer…~~ **Superseded 27 Oct:** page 17 is deleted, not re-approved.
- **Every other re-approved or moved page** keeps its current card exactly (see "Reviewed card values").
- **Pages 36–38:** check that each FAQ question sits directly above its answer.

**No script is needed.** Every step uses the admin workflow. The only approved pages that the final chunker would cut differently (16, 18, 20, 31, 32, 33, 36, 37, 38) are all replaced in steps 3–4.

**Summary:** 13 existing pages are moved or re-approved (9 re-scraped at the same URL, 4 moved to a new URL), 2 pages are added, and 11 are untouched. That gives 26 pages and 140 chunks (equal to the staging database; about 140 if a live page changes before approval).

**Validation after migration:**
1. Run `validate_migration.py --embeddings` and expect 0 failed checks. It covers counts, text, chunks, vectors, FAQ pairs and every card field.
2. Its re-embed check: stored embeddings have cosine above 0.9999 with fresh ones.
3. Compare each page's text with staging. The staging text itself is in `procedureassist_staging` and, for the changed pages, in `evidence/source_audits/staging_inputs/`. `evidence/database/staging_pages.txt` gives only the text length and chunk count per page. Explain any difference by a live page change or a scraper change.
4. Run the suite (`evidence/other/scripts/run_suite.sh` with `fixtures/evaluation/safety.json`). Compare with the **final-code staging** results (`05`, "Master reliability work"; `19`): main 75/80, held-out 23/27, identification 11/14, 35/42, 31/37, 31/36, and the safety set as on staging (`evidence/evaluations/premigration_safety/staging_safety.txt`). Repeat runs of unchanged code have been identical at temperature 0, but inspect every changed case. If the code has changed since `master_final`, re-run the staging baseline first.
5. Spot-check in the browser: EPF apprentices, IDP fee, motorcycle RC renewal and polling steps. Also check that birth, death, community and income certificate questions get no CAN-editing steps and no unrelated card. Page 17 is deleted (revised 27 Oct); this replaces the old "renamed page 17 card" check.

**Rollback:** restore the step-0 dump (see above).
- **Full rollback:** restore the dump, then check that the checksums equal the pre-migration values recorded at step 0.
- **If one page's re-approval fails mid-migration** (for example 422 or 502 at Extract, or a live page that has changed): its old record may already be deleted in step 4.
  - Either retry once the cause is fixed, or restore the step-0 dump.
  - Never save the page's staging text by script instead.
- **The staging database is not a rollback source** for the approved database. Its IDs differ, and its content was never reviewed.

## Safety rules for anyone continuing
- Never edit `.env`, print its values, or commit it.
- Never change approved records without the owner's explicit approval of the exact plan; staging approval is not approval.
- Never commit or push without being asked.
- Do not edit evaluation fixtures or expected answers.
- Never use unofficial sources as evidence.
- Only one process should drive Ollama evaluations at a time. Two sessions editing the same tree must agree who owns which files (this happened on 23 Oct; see `11_DECISION_LOG.md`).
