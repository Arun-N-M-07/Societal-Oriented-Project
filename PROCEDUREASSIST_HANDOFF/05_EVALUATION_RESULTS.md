# 05 — Evaluation results

> **Latest results (28 Oct 2026):** `22`, section D (`evidence/evaluations/p9_baseline/` after the page 17 deletion and the label changes; `p9_final/` after the approval of N3, N4 and N8). The sections below are earlier runs.

## What the evaluations are
- **Main set:** `fixtures/evaluation/answers.json`, 80 questions in 19 categories: fees, eligibility, steps, Tamil script, Romanized, mixed language, follow-ups, ambiguous, not stated, and more.
- **Held-out set:** `fixtures/evaluation/heldout.json`, 27 questions never used to tune prompts or rules. It is untracked in Git; keep it.
- **Run with:** `scripts/evaluate_answers.py [fixture]`. It calls the real API in-process (identify → guidance → relation) with the real models and writes nothing. It checks quotes and citations, and puts each failure down to a stage: normalize, identify, follow-up routing, retrieval, missed answer, incomplete, unsupported, citation, clarification.
- **How outcomes are counted:**
  - **Correct** = a verified claim cites the expected evidence.
  - **Correct (partial, flagged)** = correct, but the app flagged the answer as partial.
  - **Appropriate abstention or no match** = the question is not answerable from approved pages, and the app said so.
  - **Clarification** = the app asked which service, but an answer was expected (an unnecessary clarification).
  - **Clarification (expected)** = asking was correct.
  - **Missed answer** = the evidence was retrieved but no claim survived verification (an unnecessary abstention).
  - **Retrieval failure** = the wrong or no page was identified.
  - **Incorrect or misleading** = an unsupported claim, a wrong-page citation, or a clarification where the case expected none.
- **Safety set** (25 Oct evening): `fixtures/evaluation/safety.json`, 59 cases built from every confirmed failure (`19`, P0-1). A claim matching `forbidden`, or a card matching `card`, counts as *incorrect or misleading*. Cases whose `requires` page is not stored are skipped (6 page-39 cases on approved data). Each run also prints a separate identification count.
- **Identification sets** (`scripts/evaluate_needs.py`): `multi_need` (14), `population` (42), `demo_services` (37), `tamil` (36). Each counts messages whose services were all identified correctly.
- **Never edited:** the fixtures and expected answers were never changed. SHA-256 hashes are in `evidence/evaluations/*/frozen_inputs*.txt`.

## Code and data versions
| Label | Meaning |
|---|---|
| **Existing code** | The code at the start of 23 Oct (commit `3491415` plus earlier uncommitted rounds). It is reproduced by `run_eval.py old`, which swaps in the previous `verify_claims`; the scraper changes do not affect stored data. |
| **Updated code (22:02)** | Adds the scraper fixes (div/span/summary, table rows, `_row_context`), the heading-aware chunker, the sentence/row money rule and amounts in words. Hashes: `evidence/evaluations/eight_run_matrix/frozen_inputs_eight_runs.txt`. |
| **Final code (23:33)** | Updated code plus the named-page tie rule, the back-reference rule and the document-kind rule. Hashes: `evidence/evaluations/final_code/frozen_inputs_final.txt`. |
| **Approved DB** | `procedureassist`: 24 pages, 122 chunks, procedures md5 `016980ee…`, chunks md5 `3e45c78f…` |
| **Staging DB** | `procedureassist_staging`: 26 pages, 140 chunks, chunks md5 `93000b69…`. The procedures md5 is `8aba737f…` by `db_checksums.sql`. The other session's `frozen_inputs` file uses `md5(string_agg(id‖name‖source_url‖source_text))` instead, which gives `6154bf02…` for staging and `618bb8fb…` for approved. Both were reproduced on 24 Oct, so all staging runs used the same 26/140 snapshot (see `07`, "Integrity checks"). |

## The eight-run matrix (evidence: `evidence/evaluations/eight_run_matrix/`)
"Eight runs" means 4 configurations (existing or updated code × approved or staging data), each run on 2 sets: the main 80 and the held-out 27. The 4 identification sets were also run on both databases with the updated code.

The final code was evaluated later, in a further 4 runs (final code × both databases × both sets); see "Final code runs". The **final-code-on-staging result is no longer missing**: it is 74/80 and 23/27.
| Code | Data | Main (80) | Held-out (27) | File |
|---|---|---|---|---|
| Existing | Approved | **73/80** | **23/27** | `base80.txt`, `baseheld.txt` |
| Updated (22:02) | Approved | **73/80** | **23/27** | `code80.txt`, `codeheld.txt` |
| Existing | Staging | **71/80** | **22/27** | `oldstage80.txt`, `oldstageheld.txt` |
| Updated (22:02) | Staging | **71/80** | **23/27** | `stage80.txt`, `stageheld.txt` |

### Outcomes, main set
| Outcome | Existing/Approved | Updated/Approved | Existing/Staging | Updated/Staging | **Final/Approved** |
|---|---|---|---|---|---|
| Correct, complete | 48 | 48 | 51 | 51 | 47 |
| Correct, flagged partial | 15 | 15 | 10 | 10 | 16 |
| Appropriate abstention / no match | 8 | 8 | 8 | 8 | 8 |
| Expected clarification | 2 | 2 | 2 | 2 | 2 |
| Unnecessary clarification | 4 | 4 | 7 | 7 | 4 |
| Missed answer (unnecessary abstention) | 2 | 2 | 1 | 1 | 3 |
| Retrieval failure | 1 | 1 | 1 | 1 | 0 |
| **Incorrect or misleading** | **0** | **0** | **0** | **0** | **0** |
| **Total as expected** | 73 | 73 | 71 | 71 | **73** |

### Outcomes, held-out set
| Outcome | Existing/Approved | Updated/Approved | Existing/Staging | Updated/Staging | **Final/Approved** |
|---|---|---|---|---|---|
| Correct (complete + partial) | 19 | 19 | 16 + 2 | 17 + 2 | 20 |
| Appropriate abstention / no match | 3 | 3 | 3 | 3 | 3 |
| Expected clarification | 1 | 1 | 1 | 1 | 1 |
| Unnecessary clarification | 3 | 3 | 3 | 3 | 2 |
| Missed answer | 1 | 1 | 2 | 1 | 1 |
| **Incorrect or misleading** | **0** | **0** | **0** | **0** | **0** |
| **Total as expected** | 23 | 23 | 22 | 23 | **24** |

### Final code runs (evidence: `evidence/evaluations/final_code/`)
The output files were written at these times (IST):
- approved: 23:47 (main) and 23:49 (held-out) on 23 Oct;
- staging: 00:01 (main) and 00:03 (held-out) on 24 Oct;
- identification sets: by 00:06 on 24 Oct.

The code hashes are those of 23:33, and they still matched on 24 Oct, 00:25.
| Code | Data | Main (80) | Held-out (27) |
|---|---|---|---|
| Final (23:33) | Approved | **73/80** | **24/27** |
| Final (23:33) | Staging | **74/80** | **23/27** |

| Outcome, main set | Final/Approved | **Final/Staging** |
|---|---|---|
| Correct, complete | 47 | **52** |
| Correct, flagged partial | 16 | 12 |
| Appropriate abstention / no match | 8 | 8 |
| Expected clarification | 2 | 2 |
| Unnecessary clarification | 4 | 4 |
| Missed answer (unnecessary abstention) | 3 | 2 |
| Retrieval failure | 0 | 0 |
| **Incorrect or misleading** | **0** | **0** |

| Outcome, held-out | Final/Approved | Final/Staging |
|---|---|---|
| Correct (complete + partial) | 20 | 17 + 2 |
| Appropriate abstention / no match | 3 | 3 |
| Expected clarification | 1 | 1 |
| Unnecessary clarification | 2 | 1 |
| Missed answer | 1 | 1 |
| Retrieval failure | 0 | 1 |
| **Incorrect** | **0** | **0** |

**Failures, final code + staging, main set:**
- missed answers:
  - "At what age can I drive a transport vehicle?" (inexact quote);
  - "When is a duplicate driving licence issued?" (document-kind false rejection, H1);
- unnecessary clarifications:
  - learner vs permanent licence;
  - "I live abroad";
  - "I just turned 18";
- "How do I renew?" (asks which service).

The tie rule removed the IDP, APY and Romanized renewal-fee clarifications seen with the 22:02 code (7 → 4 unnecessary clarifications). The mixed-language Aadhaar question and the EPS contribution question pass.

**Failures, final code + staging, held-out set:**
- **The grace-period fee is now counted as a retrieval failure.** The tie rule sends it to the renewal page, and the completion from the fee table abstained: the model omitted the extra Rs. 1,000/yr, which is correctly rejected.
- Form 8 (asks to choose).
- The Tamil voter-helpline number (missed answer: generation).
- "What is the fee?" (asks which service).

**Identification sets, final code:**

| Set | Approved | Staging |
|---|---|---|
| multi_need (14) | 11 | 11 |
| population (42) | 34 | 33 |
| demo_services (37) | 30 | 30 |
| tamil (36) | 29 | 30 |

Compared with the 22:02 code on staging, population 32 → 33 and demo_services 29 → 30.

### What each comparison establishes
- **Existing → updated code on approved data: no change (73/80, 23/27).** The code fixes protect against errors that appear once the data is re-scraped (e.g. "an additional fee of Rs. 300"). They do not change answers on the old data.
- **Approved → staging data: −2 main / −1 held-out with existing code; −2 main / ±0 held-out with updated code.**
  - **Fixed on staging:** the mixed-language Aadhaar documents question; the pension-contribution question; the held-out appeal fee (the fee row is now one paragraph).
  - **New on staging:** 4 unnecessary clarifications:
    - IDP fee;
    - "Who can join APY?" (two APY pages);
    - the Romanized renewal fee;
    - "I just turned 18".
  - **Held-out regression:** the Tamil voter-helpline question. "1950" is retrieved, but the model abstains (generation).
- **Final code + staging is the best combination measured.** It scores 74/80 and 23/27 with 0 incorrect. It has the most complete answers (52) and fixes the wrong answers on approved data that the sets do not test (targeted checks below).
  - **Cost:** one held-out regression, the grace-period fee (tie rule + model omission).
  - **Remaining clarifications:** close voter and licence pairs.
- **Safety:** no run in any combination produced an "incorrect or misleading" outcome. **But the sets do not test the wrong answers found on approved data** (below), so 0 incorrect on the sets does not mean the approved data is safe.

## H1 fix runs (24 Oct 2026; evidence: `evidence/evaluations/h1_fix/`)
**Code:** the final code (23:33) plus the H1 change to `rag._section_heading` (see `10`, H1).
- Only `backend/rag.py` differs from the final-code hashes.
- The fixtures are unchanged (hashes in `frozen_inputs_h1.txt`).
- The runs took place from 00:42 to 00:58 IST on staging.
- **Checksums.** `frozen_inputs_h1.txt` records the **pre-run** checksums of both databases (and the end time); it does not contain post-run values. A post-run `db_checksums.sql` check in the H1 execution session, and another in the acceptance review, both reported the same values; these are reported results, not recorded files.
- The results above are kept as they were. This section adds to them.

| Run (staging) | Final code (baseline) | **Final + H1** | Change |
|---|---|---|---|
| Main (80) | 74/80 | **75/80** | +1 |
| Held-out (27) | 23/27 | **23/27** | none: every question has the same outcome |
| multi_need (14) | 11 | 11 | identical, message by message |
| population (42) | 33 | 33 | identical |
| demo_services (37) | 30 | 30 | identical |
| tamil (36) | 30 | 30 | identical |

| Outcome, main set | Final/Approved | Final/Staging | **Final + H1 / Staging** |
|---|---|---|---|
| Correct, complete | 47 | 52 | **54** |
| Correct, flagged partial | 16 | 12 | 11 |
| Appropriate abstention / no match | 8 | 8 | 8 |
| Expected clarification | 2 | 2 | 2 |
| Unnecessary clarification | 4 | 4 | 4 |
| Missed answer | 3 | 2 | **1** |
| **Incorrect or misleading** | 0 | 0 | **0** |

**Exactly two answers changed** (`comparison_vs_final_code.txt`). Both are on page 25 (Duplicate Driving Licence), the only page whose headings the change affects.
- "When is a duplicate driving licence issued?" went from a missed answer to 3 verified claims: the three official circumstances, each quoted exactly.
- "I lost my DL, what should I do?" went from 1 claim (partial) to 4 claims (complete): issued when lost; application in Form 2; attested photocopies in case of loss; fees as prescribed with user charges. Each claim is quoted from page 25 (`changed_staging.txt`).

The same questions give identical claims on the approved data (`changed_approved.txt`; page 25 is the same in both databases). The full approved sets were not re-run.

**Remaining failures, main (5):**
- the transport-vehicle age question (missed answer: inexact quote, H4);
- three unnecessary clarifications (H6): learner vs permanent licence, "I live abroad", "I just turned 18";
- "How do I renew?" (asks which service).

**Remaining failures, held-out (4), unchanged:** grace-period fee, Form 8, Tamil voter helpline, "What is the fee?".

Identification sets cannot change with H1, because identification does not call `verify_claims`. They were re-run to confirm this.

## Master reliability work (25 Oct 2026, evening; evidence: `evidence/evaluations/master_*`; report `19`)
Each run is from a frozen snapshot (hashes in each folder's `frozen_inputs.txt`). Database checksums were identical before and after every run.

| Evaluation | Baseline (today's code, before) | After P0-2 | Final (all changes) |
|---|---|---|---|
| Staging main / held-out | 75/80, 23/27 (identical to the H3 runs) | 75/80, 23/27 | 75/80, 23/27 (claims identical) |
| Approved main / held-out | 74/80, 24/27 (identical to the H3 runs) | 74/80, 24/27 | 74/80, 24/27 |
| multi_need / population / demo_services / tamil | 11/14, 33/42, 30/37, 30/36 | 11/14, **35/42, 31/37, 31/36** | same as P0-2 |
| Follow-up scenarios; audit probe | 17/17; — | identical | identical, except the fitness-test question now abstains instead of giving the certificate fee |
| Safety set, staging | 38/59; incorrect 2; confident wrong pages 8 | 43/59; incorrect 2; wrong pages 5 | **43/59; incorrect 1** (page 17 card); wrong pages 5 |
| Safety set, approved | 33/53; incorrect 3; confident wrong pages 7 | 38/53; incorrect 3; wrong pages 4 | **38/53; incorrect 2**: the income and nativity lists, both wrong answers under the page 17 card (labels corrected 26 Oct, `premigration_safety/`); wrong pages 4 |

**What remains wrong:**
- **Approved data:** the TN income-certificate answer (one item from the Deserted Women list) and the nativity-certificate answer (3 of 8 items from other lists), both shown under page 17's misleading card. They come from data and are fixed by the migration; staging gives both lists correctly (traced 26 Oct, `19`).
- **Still matched although out of scope, with abstaining answers:** marriage certificate ×2 and PAN name change.
- **Still missed:** the four W11 colloquial or abbreviated questions.

## H3 fix: row-group continuation and RC/DL attribution (25 Oct 2026; evidence: `evidence/evaluations/h3_fix/`)
**Final code:** the RAG reliability fixes plus `rag._item_continuation` and `rag._spell_out`; fixtures unchanged.
- All runs exited with code 0; the database checksums were identical before and after (`exit_codes.txt`, `frozen_inputs.txt`).
- Two earlier versions were measured and corrected; their runs are kept with suffixes:
  - `_run1_spec_literal`: continuation without the relevance check. It dropped row 9(b) from the hypothecation answer, 3/3 runs, because the retrieved chunk ended with item 10.
  - `_run2_B_always`: RC/DL spelled out for every claim. It rejected 8 of 9 correct "documents to renew your vehicle RC" claims; staging main 74/80, approved main 72/80.

| Run | Baseline | Final | Change |
|---|---|---|---|
| Staging main | 75/80 | **75/80** | every question the same |
| Staging held-out | 23/27 | **23/27** | every question the same |
| Approved main | 74/80 | **74/80** | every question the same |
| Approved held-out | 24/27 | **24/27** | every question the same |
| Identification sets | 11/14, 33/42, 30/37, 30/36 | same | per message identical (Tamil "single flow" 21 → 22: normalisation variance) |
| Follow-up scenarios / audit probe | 17/17; 34/42 page, 23 cited | same | no changed answer |

**H3 questions on staging, 3 runs each, all identical (`h3_questions_staging.jsonl`):**
- "…renew the registration certificate of my motorcycle?" → **Rs. 300, row 4(b)** (before: no answer).
- On page 39:
  - duplicate RC → "half of the fee against Serial No. 4" (before: the *trade certificate* fee);
  - "RC renewal fee for a car" → every row of items 4 and 16, each labelled with its item and class (before: "RC … Rs. 200" from the fitness row);
  - "renew my vehicle RC" → abstains (before: the fitness fee).
- Unchanged:
  - RC questions using the abbreviation → page 28, "fee as specified in Rule 81" (partial);
  - fitness test fee → the certificate fee (item 11), partial;
  - hypothecation fee → rows 9(a)–(c);
  - IDP Rs. 1000; DL renewal Rs. 200.
- Continuation changes 2 of 137 fixture/probe retrievals on staging (both RC questions on page 39) and 0 of 132 on approved data.

## RAG reliability fixes (25 Oct 2026; evidence: `evidence/evaluations/rag_fixes/`)
**Code:** H1 + number words + W3 + W1 + W10 (W2 built, measured, withdrawn; see `10`). Fixtures unchanged.
- Every run's exit code is recorded (`exit_codes*.txt`); all were 0.
- Database checksums were recorded before and after each run (`frozen_inputs*.txt`), and were identical.
- Earlier outputs are kept with suffixes, never overwritten:
  - `_run1_before_rowfix`: W10's first row filter;
  - `_run2_with_w2`: W2 still active.

| Run | Baseline | Final code | Change |
|---|---|---|---|
| Staging main (80) | 75/80 (H1 runs) | **75/80** | every question the same outcome |
| Staging held-out (27) | 23/27 | **23/27** | every question the same (with W2 active it was 22/27; see below) |
| Approved main (80) | 73/80 (final code, 23 Oct, before H1) | **74/80** | +1: "When is a duplicate driving licence issued?" (H1); "I lost my DL…" went from 1 partial claim to 4 claims |
| Approved held-out (27) | 24/27 | **24/27** | every question the same |
| Identification sets (staging) | 11/14, 33/42, 30/37, 30/36 | **11/14, 33/42, 30/37, 30/36** | unchanged |
| Incorrect or misleading | 0 | **0** | — |

**What the runs showed along the way (all inspected case by case):**
- **Run 1: the W10 row filter broke approved data.** Approved main fell to 71/80 and held-out to 23/27; the IDP fee, the renewal-fee follow-up, the IDP follow-up and the grace-period fee all lost their fee-table answers. The cause: approved page 27 stores the label and the amount as separate paragraphs, so no single paragraph contained the quote. The fix checks the quote together with its row; a new test covers a table stored cell by cell. Run 2 then gave 74/80 and 24/27.
- **Run 2: W2 made held-out 23 worse.** "What is the fee to renew my vehicle RC?" reached page 39 but answered with the **fitness-certificate** renewal fee (Rs. 200, flagged partial), because the RC fee rows are not retrieved (H3). The audit probe's motorcycle RC question got the over-20-years row (Rs. 2,000). W2 also moved "When can I take out my whole PF money?" from EPF to EPS. **W2 was withdrawn**; held-out 23 is back to its safe abstention (run 3, 23/27).
- **W2 had no effect on approved data** (0 of 240 decisions changed; `w2_effect_on_approved.txt`). On staging it changed only RC questions, so the approved runs and the staging main run stand for the final code.

**Targeted checks (staging):**
- **Follow-up matrix:** 17/17 scenarios end on the expected page (`followup_scenarios_staging.txt`).
  - "What about EPS?" on EPF is answered from the EPS page.
  - "What about the pension?" and "What about the certificate?" stay on the open page.
  - "And how much does it cost?" on IDP gives "Fees as prescribed…" plus "The fee for the issue of an International Driving Permit is Rs. 1000.00/-", and no other rows.
  - "What is the fee?" on DL renewal gives only its Rs. 200 row (before: all 8 rows of the table).
- **Audit probe:** 42 questions (`audit_probe_staging.txt`): correct page 34/42, as at Stage 1; answers citing the evidence went from 21 to **23**.
  - The ITR-1 income limit is now answered (W3).
  - The IDP cost follow-up is now answered (W10).
  - The probe replays the old follow-up order, so W1 is measured by the follow-up matrix instead.

## Identification regression sets (updated code, 22:02)
| Set | Approved | Staging |
|---|---|---|
| multi_need (14) | 11 | 11 |
| population (42) | 34 | 32 |
| demo_services (37) | 30 | 29 |
| tamil (36) | 29 | 30 |

The staging losses are mostly APY and "Aadhaar update at a post office" asking which page. These are new close ties from the added and re-scraped pages. With the final code these sets give 11, 33, 30 and 30 on staging (see "Final code runs" above): population and demo_services each recover one message.

## Targeted checks with the final code (evidence: `evidence/traces/targeted_*.txt`)
| Question | Approved data | Staging data |
|---|---|---|
| Can apprentices become EPF members? | **WRONG:** "Apprentices can become EPF members" | Correct: "cannot" |
| Documents for an income certificate in Tamil Nadu | **WRONG:** "Proof of Income…" (from another list) | Correct 9-item list |
| Fee for an International Driving Permit | Rs. 1000 (via the tie rule + fee table) | Same |
| Who can join APY? | India Post rule (18 to under 40) | Same, no clarification now |
| Romanized renewal fee | Rs. 200 | Rs. 200 |
| Renewal fee after the grace period | Rs. 300 + Rs. 1,000/yr (correct, full row) | Abstains (model omitted the Rs. 1,000; correctly rejected) |
| Duplicate licence fee (citizen) | Clarification between the fee table and the duplicate page | Same |
| Duplicate licence fee (driving school) | Rs. 5000 | Rs. 5000 |
| APY pension amount | Abstains (no source) | **Abstains, although PFRDA states the slabs.** Each claim must include every amount in its sentence (₹1,000–5,000); the model quotes one. Safe, but a coverage miss. |
| Can an income-tax payer join APY? | Abstains (no source) | Correct (PFRDA) |
| Motorcycle RC renewal fee | Abstains (Rule 81 page missing) | Abstains. Before the document-kind rule it **wrongly** gave the trade-certificate fee, Rs. 500. The correct row (Rs. 300) is not retrieved. |
| Imported car older than 20 years, RC renewal | Abstains | Abstains (the renewal-of-RC page is chosen, not the fee page) |
| "I just turned 18 and want to vote." | Register to Vote (answered) | Clarification |
| Polling booth steps | All 6 steps in order | All 7 including the gadgets rule, in order |

## Known-case traces (approved vs staging)
`evidence/traces/attr_main_final.txt` and `attr_staging_final.txt` trace 30 cases. Each shows:
- identification scores;
- retrieved chunk IDs with cosine similarity;
- whether each chunk holds the evidence;
- the final claims.

They were taken with the updated (22:02) code. `attr_main.txt` and `attr_staging.txt` are earlier traces from the start of the audit.

## History of headline numbers
| When | Main | Held-out | Incorrect |
|---|---|---|---|
| Before the final correctness pass | 74/80 | — | 1 incorrect, 1 incomplete |
| After the final correctness pass (verified again on 23 Oct) | 73/80 | 23/27 | 0 |
| Final code, approved data (23 Oct, 23:47) | 73/80 | 24/27 | 0 |
