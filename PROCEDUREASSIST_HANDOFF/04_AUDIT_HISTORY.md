# 04 — Audit history

Each audit records what was found, its root cause and what was done about it. The most recent audit comes first.

## Audit 9 — Master reliability execution (25 Oct 2026, evening)
- **Report:** `19_MASTER_RELIABILITY_EXECUTION.md`. Phases P0-1 to P3 plus security, each measured on both databases from a frozen code snapshot.
- **Found and fixed:**
  - US/UK questions confidently matched Indian pages: "US"/"UK" must now appear on the page.
  - The live EPF apprentice wrong answer quoted a bare "Yes" whose FAQ question had been lost: a bare Yes/No now counts only under its question.
  - The motorcycle fitness-test fee was taken from the certificate-of-fitness row (fee-service rule). The nearest heading was item 10's, which is why the rule uses only the heading directly above.
  - "RC" counted as initials of "REV-101 Community Certificate".
- **Measured and rejected:**
  - a document-type identification check (lost 5–16 correct matches);
  - the sentence-level period rule (rejected 6 correct claims, caught none);
  - any two-letter capital as a place (loses "SC certificate", "IT return").
- **Data:** the pre-migration re-scrape shows no live drift. Defects in the official pages themselves are listed in `19` (TN FAQ lists 15/16 look swapped; EPF "insolvent → Yes"; "diability"; "Form 6?"; "ofa").
- **Evidence:** `evidence/evaluations/master_*`, `evidence/investigations/{p0_2_scope, p0_3_premigration, p1_1_verification, p1_2_abbreviations, p1_3_chunking}`.

## Audit 8 — Complete system reliability audit (25 Oct 2026)
- **Report:** `18_COMPLETE_SYSTEM_RELIABILITY_AUDIT.md` (read-only).
- **Finding:** the architecture is sound. Three reasons for wrong answers: defective live data; identification without a scope model; verification that is lexical, not semantic. Seven root causes (RC1–RC7). The evaluation sets could not see the known wrong answers.

## Audit 7 — H3: fee rows on long tables (25 Oct 2026)
- **Root cause (retrieval):** item 4's rows rank below other renewal items, and the model then picks the wrong row or labels another row's fee as the RC fee.
- **Fixes:**
  - row-group continuation for the item a retrieved chunk ends with, when the question uses two of the item's words;
  - an amount claimed for an RC or a DL must come from a row about one.
- **Two regressions found and corrected during verification:** hypothecation 9(b) lost to item 10's rows; RC document lists rejected.
- **W2 stays withdrawn.**
- **Evidence:** `evidence/evaluations/h3_fix/`.

## Audit 6 — RAG reliability audit and fixes (25 Oct 2026)
- **Audit:** `12_RAG_RELIABILITY_AUDIT.md`. The architecture is sound; the weak points were identification heuristics, follow-up routing and specific verification gaps.
- **Plan:** `15_RAG_REGRESSION_TEST_PLAN.md` (Stage 2).
- **Fixed, with tests and measurement:**
  - **W3:** form and return numbers are names, not quantities. "ITR-1" was rejected as 1; "Form 30" let a wrong 30-day deadline pass both checks; "Form 6A" passed as "Form 6".
  - **W1:** a follow-up that names another procedure is answered by it ("What about EPS?" on EPF had produced an EPF fact presented as EPS).
  - **W10:** "Fees as prescribed" never makes a fee answer complete, and fee-table completion keeps only the procedure's own row.
- **Withdrawn:** W2. Correct routing to the Rule 81 page made answers worse, because its RC rows are not retrieved (H3). It must be re-done after H3.
- **Kept:** the threshold (W11).
- **Recorded:** wrong-page similarity cases (W12).
- **A regression found and fixed during verification:** W10's first row filter missed tables stored cell by cell (approved page 27).
- **Evidence:** `evidence/investigations/rag_audit/`, `evidence/investigations/stage2/`, `evidence/evaluations/rag_fixes/`.

## Audit 5 — H1: document-kind false rejection (24 Oct 2026)
- **Problem.** "When is a duplicate driving licence issued?" was a missed answer on both databases.
- **Root cause (verification).** The trace showed 3 correct claims, each with an exact quote, all rejected by the document-kind rule. Page 25 introduces its list with "A duplicate driving licence will be issued in the following circumstances", with no ":" or "?". So `_section_heading` returned `""`, and the claim's kind word appeared nowhere.
- **Fix.** `_section_heading` falls back to a short "…the following <plural>" lead-in, **only** when no "?"/":" heading is above the quote. `_is_heading` and chunking are unchanged.
- **Rejected alternative.** "Nearest lead-in wins": it would re-parent staging page 17's CAN steps.
- **Result.** Staging main 74 → 75/80, held-out unchanged at 23/27, identification sets unchanged, 0 incorrect. Two answers improved, both on page 25.
- **Evidence:** `evidence/evaluations/h1_fix/`. Details and limitations: `10`, H1.
- **Status:** not committed; waiting for the owner's review.

## Audit 4 — Source audit and final validation (23 Oct 2026)

**Question:** do the approved pages actually contain the right official information, and does the app use it?

| Finding | Evidence | Root-cause stage | Action |
|---|---|---|---|
| EPFO pages lost all FAQ questions (27) and the "Who it covers" cards. | Stored text has bare "Yes"/"No". "Can apprentices become EPF members?" got "Apprentices can become EPF members", but the official answer is No. | Scraping (`div`/`summary` text dropped) | Scraper fix; re-scrape 36–38 (pending approval) |
| Tamil Nadu e-Sevai FAQ lost its 18 questions, so its 10 document lists are unlabelled. | Income-certificate question answered with "Proof of Income" from another list. The community-certificate question got Salary Certificate and PAN from other lists. | Scraping | Scraper fix; re-scrape 17, which must also be renamed (its stored steps are for editing CAN details) |
| The fee table stored each cell as its own paragraph. | Cells "10", label and amount were separate paragraphs, so a fee was cut off from its purpose. | Scraping | One paragraph per table row; re-scrape 27 and 35 |
| The Rule 81 vehicle fee table was missing. | Pages 28–30 say only "fee as specified in Rule 81". | Source coverage | Add the Parivahan fees-and-user-charges page |
| APY amounts are only in PDFs. | India Post page 34 | Source coverage | Add PFRDA's APY page |
| Menu pollution on income-tax manuals; identical menu chunks 82/91/96. | Chunk text | Scraping | `?mobile-app=1` address |
| Gallery noise on ECI pages. | Stored text | Scraping | Re-scrape 19 and 20 |
| Polling steps split across chunks. | Staging trace omitted the first step. | Chunking | Heading-aware chunk start |
| "Additional Rs. 300" after the grace period. | Staging trace | Verification | Sentence/row money rule |
| Motorcycle RC renewal reported as Rs. 500 (the trade-certificate fee). | Staging trace: the right row was not retrieved; the meaning check approved the wrong one 3/3. | Retrieval + verification | Document-kind rule |
| Renewal follow-up answered "A fee of Rs. 30/-" with no condition. | Evaluation follow-up case | Verification (citation meaning) | Back-reference rule |
| Needless clarifications between a service page and a page naming it. | Staging evaluation | Identification | Named-page tie rule |

Confirmed gaps, with no first-party source found:
- passport fee amounts (calculator only; fees revised from 1 Jul 2026);
- the PAN–Aadhaar fee amount;
- the APY contribution chart;
- the UIDAI accepted-documents list (a PDF);
- a citizen duplicate driving-licence fee;
- community-certificate application steps;
- learner's-licence application steps.

## Audit 3 — Final correctness pass (before 23 Oct)
- **Applicant-type fee error.** A citizen asking about their own duplicate licence got the driving-school fee. Root cause: generation, plus a meaning check that failed 3/3. Fix: the deterministic `APPLICANT_LIMIT` rule.
- **Polling answers incomplete.** Root cause: generation. Fix: the "official order from the first step" instruction.
- **VVPAT retrieval miss.** The question scored 0.522, below the 0.53 threshold. Fix: the single-page abbreviation rule. Diagnostic questions showed no false matches for GST, UPI, KYC, PUC or EPIC.
- **Cleanup proposal for pages 31, 32, 33, 19 and 20 (menus and galleries).** This was superseded by audit 4's plan.

## Audits 1–2 — Reliability audits (Oct 2026)
- **Full-system query reliability.** Added clarification for questions that name no service, multi-need handling, the follow-up order (the open page first, then a new search), per-claim citations from related pages and the `partial` flag. The evaluation script now names the failing stage.
- **Before then:** the negation-flip check (`7314202`) and the README limitations (`81f2a4f`).

Older reports were written in chat, not in files. This folder is now the record.

## Issue register (detailed)
**Status values:**
- **Fixed in code (verified)**: tests pass and the behaviour was seen in targeted or evaluation runs.
- **Fixed in data (staging only)**: needs the migration approval.
- **Proposed**: designed but not built.
- **Open**: no fix yet.

**Files:**
- R = `backend/rag.py`
- S = `backend/scraper.py`
- P = `backend/procedure_search.py`
- tests: `tests/test_guidance.py` (G), `test_rag.py` (RG), `test_scraper.py` (SC), `test_identify.py` (I)

| # | Issue (example) | Expected | Actual (before) | Root cause | Change | Files and tests | Status | Remaining risk |
|---|---|---|---|---|---|---|---|---|
| 1 | EPF apprentice eligibility: "Can apprentices become EPF members?" | "No. But when he ceases to be an apprentice he should be enrolled immediately." | "Apprentices can become EPF members" | Scraping: FAQ questions in `<summary>` dropped, bare "Yes/No" answers left, model paired a wrong answer | Scraper keeps `summary`/div text; page 36 re-scraped in staging | S; SC `test_keeps_text_held_directly_in_divs_spans_and_accordion_questions` | **Fixed in data (staging only)**: still wrong on approved data | Until migration, live answer is wrong |
| 2 | TN income-certificate documents | The 9 items under question 9 | "Proof of Income…" from another certificate's list | Scraping: accordion questions (`<a>` in `<div>`) dropped, lists unlabelled | Same scraper fix; the document-kind rule also rejects items from another list's section | S, R; SC, G `test_the_document_kind_may_come_from_the_question_a_list_answers` | Fixed in data (staging only) | Same |
| 3 | Citizen vs driving-school duplicate fee | Citizen: no fee stated, so abstain; school: Rs. 5000 | Citizen got the school's Rs. 5000 | Generation; model meaning check failed 3/3 | Deterministic `APPLICANT_LIMIT` / `_for_the_asker` | R; G `ApplicantLimitTest` | Fixed in code (verified) | Citizen question now gets a clarification (fee table vs duplicate page) |
| 4 | Renewal base fee and late fee | Rs. 200 renewal; Rs. 30 if more than 30 days late (with condition); Rs. 300 + Rs. 1,000/yr after grace period | Follow-up "How much is the renewal fee?" answered "A fee of Rs. 30/- will be realised", without its condition | Verification: the quote opened with "In such cases" | `BACK_REFERENCE` rule | R; G `test_a_quote_opening_with_a_back_reference_needs_the_sentence_it_refers_to` | Fixed in code (verified: follow-ups 8/8) | — |
| 5 | Motorcycle RC renewal fee | Rs. 300 (Rule 81 item 4(b)) | Staging: "Rupees Five Hundred" (the trade-certificate fee) | Retrieval missed the right row, and the meaning check accepted the trade-certificate row 3/3 | Document-kind rule | R; G `test_a_fee_is_not_moved_to_another_kind_of_document` | Fixed in code (now abstains) | Right row not retrieved (H3 in `10`) |
| 6 | Wrong document-type evidence accepted | Claim and quote about the same document | See 5 and 2 | Verification gap | `_document_kinds` + `_section_heading` | R; G | Fixed in code | The false rejection "When is a duplicate driving licence issued?" (H1) was **fixed in code on 24 Oct** (lead-in fallback, audit 5). Lead-ins worded differently, and repeated list items, can still be falsely rejected. |
| 7 | Missing conditional context in fee citations ("additional Rs. 300 after grace period") | Rs. 300 *and* the Rs. 1,000/yr | Rs. 300 called "additional", Rs. 1,000 dropped | Generation; meaning check approved 3/3 | Money rule, at sentence/row level | R; G `test_every_amount…`, `test_a_quote_cut_from_a_fee_row…`, `test_separate_sentences…` | Fixed in code (verified) | APY slabs over-rejected (H2) |
| 8 | Polling-booth step order | Steps 1–6 in order, with the officials | Missing ID check and inking; on staging, the first step was missing | Generation (before); chunking split the list (staging) | Prompt "official order from the first step"; heading-aware chunk start | R; RG `test_starts_the_next_chunk_at_the_heading…` | Fixed (verified on both databases) | — |
| 9 | VVPAT retrieval: "How long is the VVPAT slip shown?" | 7 seconds, from How to Vote | No match (0.522 < 0.53) | Retrieval: mixed-content chunk, abbreviation not in any page name | Single-page abbreviation rule | P; I `test_an_abbreviation_only_one_nearby_page…` | Fixed (verified) | — |
| 10 | NOTA information | "You can press NOTA…; last button on the EVM" | Answered | — | — | — | Works (polling answers include it) | — |
| 11 | APY eligibility and pension amounts | 18–40 (India Post); income-tax payers excluded; ₹1,000–5,000 slabs (PFRDA) | Tax exclusion and slabs not answerable (not stored); "Who can join APY?" asked to choose on staging | Source coverage; identification tie | PFRDA page added in staging; named-page tie rule | P; I `NamedByTheOthersTest` | Partly: eligibility and tax exclusion answered on staging; **pension slabs abstain** | H2 |
| 12 | Passport fee | Abstain (no amount on the official page) | Earlier: "Calculate the fee for Passport" shown as a fact | Generation (a link is not a fact) | Prompt and check: "a link is not a fact" | R | Fixed (abstains) | Fees are a source gap |
| 13 | Aadhaar address proof | The list of accepted documents | Abstains, or partial | Source: the list is a PDF | — | — | Open (gap) | — |
| 14 | Vehicle or transport age: "At what age can I drive a transport vehicle?" | 20 years | Missed answer (varies) | Generation: inexact quote ("The applicant" vs "An applicant") | None: verification must not be loosened | — | Open (H4) | — |
| 15 | Held-out appeal-fee question | Rs. 500 (rule 29 appeal) | Missed on approved data | Data: label and amount in separate paragraphs; model swaps them | Row-level scraping (staging) | S | Fixed in data (staging) | Until migration |
| 16 | Ambiguous service identification: "How do I renew?" | Ask which service | Asks | By design | — | P `names_something` | Works | — |
| 17 | Identification tie-breaking (IDP fee: IDP page vs fee table) | Answer directly | Asked to choose | Close scores between a service page and a page naming it | Named-page tie rule | P; I | Fixed in code (verified on approved data and targeted staging) | Not yet measured on staging sets (C2) |
| 18 | HTML content loss | All visible text | Text in `div`/`span`/`summary` dropped | Scraper only read p/li/td/h* | `_is_block` | S; SC | Fixed in code; data pending | — |
| 19 | FAQ / eligibility extraction (EPFO "Who it covers" cards, age 18–54) | Answer the age limit | Abstained | Same as 18 | Same | S | Fixed in data (staging) | — |
| 20 | Table and fee-row chunking | Each fee with its purpose | Cells split into separate paragraphs | Scraper | One paragraph per `<tr>` | S; SC `test_keeps_each_table_row_together_with_its_fee` | Fixed in code; data pending | — |
| 21 | Parent heading preservation (Rule 81 sub-rows) | "(b) Motor cycle" known to be RC registration | Continuation chunks lacked the parent | Chunking and table structure | `_row_context` (sub-row carries its parent row); the heading-repeat approach was rejected | S; SC | Fixed (staging page 39) | — |
| 22 | Misleading fee claims (general) | Never a wrong amount | See 3, 5, 7 | — | Applicant, money, document-kind and back-reference rules | R | Fixed in code | Meaning check still model-based |
| 23 | Unnecessary clarification and abstention | Answer when the evidence is there | 4–7 unnecessary clarifications; 1–3 missed answers per run | Ties; strict verification; 8B model | Tie rule (clarifications); no loosening | P | Partly fixed; H1 fixed 24 Oct (missed answers on staging: 2 → 1) | H2, H4, H6 |

Other findings from the 23 Oct audit:
- **Page 17 is misnamed.** "REV-101 Community Certificate" holds CAN-editing steps; it must be renamed at re-approval.
- **EDLI page contradicts itself** on the maximum benefit (₹7 lakh vs Rs.6,00,000).
- **Two sessions on one working tree.** A Claude session and its fork edited the same tree. A rejected chunker variant briefly changed staging chunks; the staging data was rebuilt and checked against the final chunker before evaluation.
