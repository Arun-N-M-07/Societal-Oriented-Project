I recommend approving the staging changes, but only together with a separate fix for the new clarifications, and not as a score improvement. On the evaluation sets, staging scores slightly lower (71/80 vs 73/80). In return, it removes three wrong answers on the approved database that the sets never test. No run in any combination gave an incorrect answer. Nothing in the approved database has been changed; it needs your go-ahead.

### 1. The eight evaluation runs
Each run used frozen code (file hashes recorded at 22:02) and the same fixtures; neither question file was changed. Approved database: 24 pages, 122 chunks. Staging: 26 pages, 140 chunks.

| Code | Data | 80-question set | 27-question held-out |
|---|---|---|---|
| Existing | Approved | **73/80** (confirms the baseline) | **23/27** |
| Updated | Approved | **73/80**, same failures | **23/27**, same |
| Existing | Staging | **71/80** | **22/27** |
| Updated | Staging | **71/80** | **23/27** |

| Outcome, 80 questions | Approved data | Staging |
|---|---|---|
| Correct, complete | 48 | 51 |
| Correct, flagged partial | 15 | 10 |
| Appropriate abstention or no match | 8 | 8 |
| Expected clarification | 2 | 2 |
| Unnecessary clarification | 4 | 7 |
| Missed answer | 2 | 1 |
| Retrieval failure | 1 | 1 |
| **Incorrect or misleading** | **0** | **0** |

On the held-out set, updated code with staging gives 17 complete, 2 partial, 3 abstentions, 1 expected and 3 unnecessary clarifications, 1 missed answer, and 0 incorrect.

**What each change did on these sets:**
- **Code alone:** no change on the sets. Its value shows on re-scraped data. Without it, a cut-off quote produced "an additional fee of Rs. 300 after the grace period", which wrongly drops the extra Rs. 1,000 a year.
- **Re-scraped data, fixed:** the mixed-language Aadhaar documents question, the pension-contribution question, and the held-out appeal fee. The fee table now keeps "Rs. 500.00/-" in the same row as "An appeal against the orders of licensing authority".
- **Re-scraped data, new clarifications (4):** IDP fee, "Who can join APY?" (two APY pages), the Romanized renewal fee, and "I just turned 18". These are close-score ties of 0.03 or less. None is a wrong answer, but each is a real usability cost.
- **Held-out regression:** the Tamil voter-helpline question. Staging retrieves the "1950" passage but the model abstains (a generation failure).
- **Identification sets on staging:** multi_need 11 → 11, population 34 → 32, demo_services 30 → 29, tamil 29 → 30. The losses are mostly APY and "Aadhaar update at post office" now asking which page.

### 2. Known cases traced through the full pipeline (approved → staging)

| Case | Approved data | Staging | Root cause |
|---|---|---|---|
| Can apprentices join EPF? | **Wrong:** "can become members"; official answer is No | Correct | Scraping dropped every FAQ question, leaving bare Yes/No answers |
| Tamil Nadu income-certificate documents | **Wrong:** a document from another certificate's list | Correct list | Scraping dropped the FAQ question that labels each list |
| Tamil Nadu community-certificate documents | **Wrong:** Salary Certificate, PAN, Encumbrance Certificate and more from other lists | Abstains, though the correct list is the top chunk | Scraping on approved data; generation failure on staging (safe) |
| EPF age limit | Abstains | "Age group: 18–54 years" | Scraping dropped text in `<div>` tags |
| Citizen vs school duplicate-licence fee | Citizen abstains; school gets Rs. 5,000 | Same | No citizen duplicate fee on any official page, so abstaining is right |
| Renewal fee and late charge | Rs. 200; Rs. 30 late fee | Same | — |
| Grace-period fee | Clarification (renewal vs fee page) | Same | Identification tie |
| Polling-booth steps | Complete, in order | Complete, in order | A chunk boundary had split the steps; the chunker fix keeps the section together |
| VVPAT duration | 7 seconds | 7 seconds | — |
| Aadhaar address proof | Abstains | Abstains in English; partial in mixed language | The full accepted-documents list is a PDF, which the app can't read |
| Transport-vehicle age | Varies | Abstains | The model quotes "The applicant…" where the page says "An applicant…", so verification correctly rejects it |
| Passport fee | Abstains | Abstains | The official page has only an interactive calculator; fees revised from 1 Jul 2026 |
| Car registration-renewal fee | Abstains (page refers to "Rule 81", which no page had) | Clarification between two pages, both of which have it | Missing source, now added |
| EDLI maximum benefit | ₹7 lakh | Rs. 6,00,000, flagged partial | The official page contradicts itself |

### 3. Code changes this round, all with regression tests
- **Scraper:** keeps text in `<div>`, `<span>` and accordion `<summary>` tags, and keeps each table row as one paragraph.
  - In fee schedules, a sub-row also carries its numbered parent row, e.g. "4. Issue or renewal of certificate of registration…: (b) Motor cycle Rupees Three Hundred Only".
  - Checked on page 39: no sub-row lacks its parent, and a sibling "(d)" row never inherits the "(c)" heading.
- **Chunker:** a new chunk starts at a section question or lead-in, i.e. a line ending in "?" or ":" ("How do I vote in person?").
  - Short list items such as "Photo" are not treated as headings, and no text is lost on any page.
  - I tried repeating section headings on later chunks and reverted it, because it attached old headings to unrelated fees.
- **Verification:**
  - Every amount in the sentence or table row a quote comes from must appear in the claim.
  - Amounts written like "Twenty thousand rupees" are now recognised.
  - Nothing was loosened.

### 4. Source audit (full URL-by-URL table in `/private/tmp/claude-501/-Users-arunnm-Projects-SOP/db3bcd4a-2175-4a9c-b255-6119f2c7a242/scratchpad/audit2/SOURCE_AUDIT.md`)
- All 24 stored pages load, and none is a homepage, navigation page, broken page or duplicate.
  - **Useful and informative (16):** pages 16, 18–21, 23–27, 32, 33 and 35–38.
  - **Useful but incomplete (8):**
    - 15: passport fees are only a calculator link.
    - 17: this record is mislabelled as "Community Certificate", but its steps are for editing your CAN details.
    - 22: learner's licence has no application steps.
    - 28–30: these vehicle pages refer to a fee table no page contained.
    - 31: the PAN–Aadhaar fee amount isn't stated.
    - 34: APY amounts are only in PDFs.
- Being reachable didn't make a page well-stored. Nine pages lost or polluted meaningful content when scraped. On the EPFO pages, for example, all 27 FAQ questions and the eligibility details were missing.
- **Staging adds two verified official pages:**
  - Parivahan's Rule 81 vehicle fee schedule.
  - PFRDA's APY page, which adds the rule that income-tax payers can't join from 1 Oct 2022 and the pension amounts. It complements rather than replaces India Post's page.
- **Gaps that remain:**
  - Passport fee amounts.
  - The PAN–Aadhaar fee amount.
  - The APY contribution chart (PDF).
  - The full Aadhaar documents list (PDF).
  - The citizen duplicate-licence fee.
  - Steps for applying for a community certificate.

### 5. Proposed database changes (awaiting your approval)
Each removed record's chunks and embeddings are deleted with it; nothing else refers to them. The replacements go through the admin extract, review and approve workflow.

1. **Add:** the Parivahan fee schedule and the PFRDA APY page.
2. **Switch to the menu-free `?mobile-app=1` address** of the same official manual, adding the new record before deleting the old one, so there is no gap:
   - page 16 (chunks 15–32)
   - page 31 (82–90)
   - page 32 (91–95)
   - page 33 (96–112)
3. **Re-scrape at the same address** (delete, then re-approve straight away; there is a brief gap because each address must be unique):
   - page 17 (chunks 33–36); the reviewer must rename it and fix its steps
   - page 18 (37–46)
   - page 19 (47–50)
   - page 20 (51–56)
   - page 27 (69–70)
   - page 35 (115–117)
   - page 36 (118–122)
   - page 37 (123–126)
   - page 38 (127–129)
4. **No change:** 15, 21–26, 28–30, 34.

**Backup and safety:**
- The approved database still matches its backup exactly (24 pages, 122 chunks, same checksums).
- Backup: `/Users/arunnm/Projects/SOP-backups/procedureassist_2026-10-23_before_source_cleanup.dump`. It is readable and contains no credentials.
- Restore: `dropdb procedureassist && createdb procedureassist && pg_restore -d procedureassist <dump>`.
- The staging copy is a separate database, `procedureassist_staging`.

### 6. Tests and checks
- **Backend:** 199 tests pass with the documented `discover -s tests` command.
  - Running one test module directly fails because the tests import `db_support` as a top-level module. That predates this session and is in the last commit; `discover -s tests -p test_rag.py` passes.
- **Frontend:** 61 tests, TypeScript, the unused-code check and the build all pass.
- **Live API on the restarted backend:** authentication returns 401 and an empty question returns 422. Fee, applicant, passport and VVPAT answers are as described above, and the server log shows no errors.
- **Browser:** the grace-period question first got a clarification. After I chose the fee page it abstained, although the same API call had just answered fully. That is the generation variance seen throughout.

### Recommendation
- **Approve the staging changes for correctness.** They remove three wrong answers that citizens can hit today: EPF apprentices, Tamil Nadu income-certificate documents and Tamil Nadu community-certificate documents. Every run kept zero incorrect answers.
- **The cost is usability, not safety:** four more clarification prompts and a few more abstentions where the model fails to use evidence it was given. These come from overlapping pages and an 8B model that doesn't use the evidence reliably.
- **Follow-up fix:** prefer the service's own page when the other close match is a fee page that merely names it. That would address the IDP, renewal-fee and grace-period clarifications. I haven't built it, so its effect is unmeasured.

**Git and other state:**
- Commit `3491415`. Nothing is staged.
- 16 files are modified, unstaged. `fixtures/evaluation/heldout.json` is untracked. Nothing is committed or pushed, and `.env` is untouched.
- A second Claude session was editing this same working tree. We agreed I'd finish the work, I kept its `verify_claims` refinement, and it is paused.

Do you approve the steps in section 5?

Sources:
- [Passport Seva fee calculator](https://www.passportindia.gov.in/psp/FeeCalculator)
- [PFRDA – Atal Pension Yojana](https://www.pfrda.org.in/schemes/atal-pension-yojana-apy)
- [NPS Trust – APY eligibility](https://npstrust.org.in/apy-eligibility)
- [Parivahan – Fees & User Charges](https://parivahan.gov.in/en/content/fees-and-user-charges)
- [Income Tax e-Filing – Link Aadhaar user manual](https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/link-aadhaar-um)