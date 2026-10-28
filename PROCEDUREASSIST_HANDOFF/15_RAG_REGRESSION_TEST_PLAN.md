# 15 — RAG regression test plan (Stage 2 preparation, 25 Oct 2026)

**What this is:** preparation only. No application code, test, fixture, database, `.env`, model setting or Git state was changed. This plan sets out how W1, W2, W3, W10 and W11/W12 from `12_RAG_RELIABILITY_AUDIT.md` should be tested before and after each fix.

**Code state planned against:** `backend/rag.py` `2eb8f9ff…`, `tests/test_guidance.py` `97cc1f7b…`, uncommitted on top of `3491415`.

**Baseline, executed 25 Oct 09:09 IST:**
- backend `REQUIRE_DB_TESTS=1 .venv/bin/python -m unittest discover -s tests`: **209 OK**;
- frontend `npm test --prefix frontend`: **61 passed**.

**Test labels used below:**

| Label | Meaning |
|---|---|
| **Existing** | Already in the repository. Its last executed result is given. |
| **New** | Proposed, not written yet. Never executed. |
| **Reproduction** | The failing behaviour, executed in a read-only script on staging or with synthetic passages; the result shown is what happened. |
| **Exploratory** | A read-only simulation of a *proposed* change, run in memory; it informs the design but proves nothing about a real implementation. |

**Evidence:**
- Stage 1 evidence is preserved in `evidence/investigations/rag_audit/`.
- The Stage 2 scripts and outputs are in the temporary folder `/private/tmp/claude-501/-Users-arunnm-Projects-SOP/bebaf14e-7bdf-4da2-8b3f-9c2a6edb540d/scratchpad/stage2/`: `w1_followups*`, `w1_guard_sim*`, `w1_refined_sim*`, `w2_w11_sim*`, `w3_identifiers.txt`, `w3_reproduction.txt`, `w3c4_w10*`. They are **not** preserved yet, because this stage may write only the evidence copy and this file. They should be copied to `evidence/investigations/stage2/` once approved.
- *Update, 25 Oct:* they are now preserved in `evidence/investigations/stage2/` (SHA-256 in `SHA256SUMS.txt`). Implementation results are in `10` ("RAG reliability fixes") and `05`.

---

## 1. W1 — follow-up routing

### Functions involved
- `frontend/src/CitizenPage.tsx::handleSend` (line 248) sends a follow-up to `answerFollowUp` when a procedure is open.
- `answerFollowUp` (line 162): `answer(id, message)` on the open page; **only if** `insufficient_evidence`, it calls `identifyProcedure` and moves to a different matched page (`showAndAnswer`).
- Backend: `routes.guidance` (line 363), `rag.answer_question` / `check_claims`, `routes.identify_procedure` (line 323) → `procedure_search.identify` / `_decide`.
- The helpers the fix would reuse: `procedure_search.abbreviates` (line 103), and the name-word test inside `named_by_the_others` (line 110).

### What the evidence shows (Reproduction and Exploratory, staging)
- **The bug only appears when the open page answers.** A1 ("What about EPS?" with EPF open) was answered from EPF with *"Employees below ₹15,000 per month (mandatory) are covered under EPS"*. In A2–A5 the open page abstained, and the existing fallback switched correctly.
- **Rejected design 1, "switch whenever the follow-up alone matches another page":** C3 ("What about the certificate?" with RC renewal open) matches **page 17, an unrelated TN FAQ** (0.582). C1 ("What about the pension?" with EPF open) matches EPS.
- **Rejected design 2, "/api/guidance declines when the question names another procedure":** it would fire on **16/92** English fixture cases. Most are fee questions correctly answered by the fee table (27), which names other services, for example "How much does a learner's licence cost?".
- **Proposed design (exploratory, `w1_refined_sim.txt`).** On a follow-up, switch early only if **both** hold:
  - `/api/identify` on the follow-up alone returns `matched` page Y, with Y ≠ the open page;
  - the follow-up **names** Y (an abbreviation of Y's name via `abbreviates`, or every word of Y's name, using the `named_by_the_others` word test).

  Otherwise behaviour is unchanged.
  - **Result:** switches for A1–A4 and X2. **No early switch** for any of the 8 fixture follow-ups (answers 62–69), nor for C1, C3 or X1.

### Smallest correction (proposal)
- **Backend:** `IdentifyResponse` gains one boolean (e.g. `named`). It is true when the matched procedure is named by the question; the helper reuses `abbreviates` and the name-word test.
- **Frontend:** `answerFollowUp` calls `identifyProcedure` first. If `matched`, `named`, and the page differs from the open one, it calls `showAndAnswer` on that page. Otherwise the current order is kept.
- **Contract change, needs approval:** the existing frontend test *"are not searched again when the open procedure answers them"* (`CitizenPage.test.tsx`, line 514) asserts `identifyProcedure` is called once. Under this design it is called for every follow-up, so that assertion must change to "**not answered elsewhere** when the open procedure answers and the follow-up names no other procedure".

### W1 test matrix

Expected routing for every case. "Stay" means answered from the open page; existing completion from a naming page is allowed.

| ID | Open page | Follow-up | Expected | Current (Reproduction) | Proposed (Exploratory) | Type of test to add |
|---|---|---|---|---|---|---|
| A1 | 36 EPF | What about EPS? | **Switch to 37**; no EPF fact presented as EPS | Answered from 36; **misattributed claim** | Switch 37 | New (frontend mock, backend `named` flag) |
| A2 | 36 EPF | How do I claim EDLI insurance? | Switch to 38 | Open page abstains → fallback → 38 | Early switch 38 | New |
| A3 | 22 Learner | How do I register to vote? | Switch to 19 | Abstains → fallback → 19 | Early switch 19 | New |
| A4 | 15 Passport | And what about linking PAN with Aadhaar? | Switch to 31 | Abstains → fallback → 31 | Early switch 31 | New |
| A5 | 19 Register to Vote | What about voters living abroad? (indirect) | Switch to 21 | Abstains → fallback → 21 | No early switch (name not used); existing fallback still switches | New (pins the fallback) |
| X2 | 36 EPF | How much of my employer's share goes to EPS? | Switch to 37 accepted | — | Switch 37 | New |
| B1 | 26 IDP | And how much does it cost? | Stay | "Fees as prescribed…" (see W10) | Stay | New |
| B2 | 23 Permanent DL | What documents are required? | Stay | 2 claims (partial) | Stay | New |
| B3 | 36 EPF | What is the eligibility? | Stay | 3 EPF claims | Stay | New |
| B4 | 15 Passport | What about the application process? | Stay | 3 claims (partial) | Stay | New |
| B5 | 24 DL renewal | Can I do it online? | Stay (abstain if not stated) | Abstained | Stay | New |
| B6 | 30 Ownership transfer | What if the owner died? | Stay | 1 claim (partial) | Stay | New |
| C1 | 36 EPF | What about the pension? | Stay or ask; **never present an EPF fact as EPS** | 12 EPF claims, none attributed to EPS | Stay (identify alone matches 37 but the question doesn't name it) | New (negative) |
| C2 | 24 DL renewal | What is the fee? | Stay; completion from 27 allowed | 8 claims from 27 (partial) | Stay | New |
| C3 | 28 RC renewal | What about the certificate? | Stay; **never move to page 17** | 5 claims from 28 | Stay (identify alone matches 17 but the question doesn't name it) | New (negative) |
| C4 | 18 Aadhaar update | Can I do this at a post office? | Stay, or switch to 35 only if confident | Abstained; identify no_match | Stay | New |
| X1 | 36 EPF | Is EPS part of EPF? | Stay (names both) | — | Stay (identify ambiguous) | New |
| F62–F69 | the 8 fixture follow-ups | as in `answers.json` | Unchanged results | Pass (H1 baseline) | No early switch in any of them | Existing (evaluation) |

**Rules every W1 test enforces:**
- A procedure named explicitly never inherits the previous page's evidence (A1, X2).
- A same-procedure follow-up is never redirected (B1–B6).
- An ambiguous follow-up never switches to an unrelated page (C1, C3, C4).

---

## 2. W2 — the abbreviation rule overriding a strong match

### Function involved
`procedure_search._decide`, lines 131–141 (`if len(named) == 1: status, ids = "matched", named`), together with `abbreviates` (line 103).

### What the evidence shows
- **Reproduction** (`evidence/investigations/rag_audit/README.md`): "What is the fee to renew the RC of a motorcycle?"
  - `classify` → matched page 39 (0.654; next 0.539);
  - "RC" abbreviates *Renewal of Vehicle Registration Certificate* (initials RVRC), so the rule switched to page 28;
  - the answer was "Pay appropriate fee as specified in Rule 81…".
- **The override is partly intentional and tested.** `test_an_abbreviation_naming_one_close_candidate_decides` (`tests/test_identify.py`, line 230) asserts *"It also overrides a confident match on the other scheme"*: "Can I withdraw my EPF?" → EPF while the scores lean towards EPS (0.75 vs 0.66). **So "never override a confident match" is wrong, and would break that test.**
- **The difference** is that EPF is the page's own name (the initials **start** "EPF…"). RC is the *document* the page deals with (the initials **end** "…RC").

### Smallest correction (proposal; no new numeric threshold)
- Keep `abbreviates` and the close-call behaviour unchanged.
- In `_decide` only, when `classify` already returned `matched` X and the abbreviation names a different page Y: override only if the abbreviation is Y's **own name**, meaning literal in Y's name ("(EPS)") or the **start** of Y's initials ("EPF" for *Employees' Provident Fund Scheme*). Otherwise keep X.

### Exploratory simulation (`w2_w11_sim.txt`; `_decide` on the whole message, 240 English messages)
- Outcomes change for **3 of 240**, all RC fee questions, all moving from page 28 to page 39:
  - held-out 23 "What is the fee to renew my vehicle RC?";
  - "What is the fee to renew the RC of a motorcycle?";
  - "RC renewal fee for a car".
- Every EPF, EPS, EDLI, DL, PAN and RC-documents case is unchanged.
- **Evaluation conflict, the owner's decision:** held-out 23 expects `renewal-of-rc` with `answer: false` (*"no approved page contains Rule 81"*). On **staging**, page 39 contains Rule 81, so the correction would give a correct, cited answer that the frozen fixture scores as a failure (staging held-out 23 → 22 possible). On approved data there is no page 39 and nothing changes. The fixture is not to be edited; the result must be reported with this explanation.

### W2 test matrix (all New unless marked; backend `IdentifyApiTest` style, synthetic vectors)

| ID | Case | Expected |
|---|---|---|
| W2-1 | Clear full-name match ("renew the registration certificate", page 28 scores best) | Page 28 |
| W2-2 | Clear abbreviation that is the page's own name ("Can I withdraw my EPF?" while EPS scores higher, 0.75/0.66) | EPF (**Existing**: `test_an_abbreviation_naming_one_close_candidate_decides`, last run passed) |
| W2-3 | Strong candidate whose name does not contain the abbreviation (fee table 0.654) vs a weaker page whose initials *end* in RC (0.530) | **Keep the strong candidate** (fails today; reproduction above) |
| W2-4 | Weaker candidate chosen only by the RC rule, no confident match (close call or no match) | Unchanged from today: RC may decide |
| W2-5 | Close call where the abbreviation legitimately helps (EPS vs EPF tie; VVPAT near miss) | Unchanged (**Existing**: `test_an_abbreviation_naming_one_close_candidate_decides`, `test_an_abbreviation_only_one_nearby_page_uses_decides_a_near_miss`, `test_a_bare_acronym_in_a_procedure_name_rescues_a_near_miss`) |
| W2-6 | RC genuinely meaning the renewal page ("How do I renew my RC?", page 28 best) | Page 28 (Exploratory: unchanged) |
| W2-7 | RC with another possible reading ("RC" also matches *REV-101 Community Certificate* by initials) | Not selected unless nearby and decided as today; never overrides a confident match |
| W2-8 | `abbreviates` unit cases | Unchanged (**Existing** `AbbreviatesTest`, last run passed) |

---

## 3. W3 — numbers inside names

### Functions involved
`rag._numbers` (line 203), `rag.verify_claims` (line 313; the number checks), and `rag._section_heading` (line 295), which would be reused.

### What the evidence shows
- **Identifiers in the stored text** (`w3_identifiers.txt`, both databases):
  - hyphenated: ITR-1 (10), ITR-2 (5), REV-101, EPS-95, Tier-1, SSR-2023, **Form-8**, **Rule-15**;
  - "Form N": Form 6A (6), Form 6 (5), Form 60 (5), Form 30, 31, 32 and others;
  - "Rule/Section N": rule 81, u/s 112A, Section 139(1), 80CCD;
  - digit + letter: 112A, 6A, 115AD, 80G.
  - Procedure names containing digits: *File ITR-1 (Sahaj) Online*, *Filing of ITR-2*, *REV-101 Community Certificate*.
- **Reproduction** (`w3_reproduction.txt`, current `verify_claims`, executed). Three defects:
  - "ITR-1" in a claim is read as the number 1, so the correct claim is **rejected**;
  - "Apply within **thirty** days" passes against "within **fourteen** days … in **Form 30**", because the form number supplies 30;
  - "Form **6A**" passes against "Form **6**", because 6A is read as 6.
- **The meaning check doesn't stop the Form 30 case.** It passed both `verify_claims` and `check_claims` 3/3 (`w3c4_w10.txt`). The claim was injected; real generation has not been seen to produce it.
- **A rejected first design** (exempt identifier digits in the claim when the identifier appears anywhere in the passage) fixed only the ITR-1 case and missed the Form 30 and 6A cases.

### Smallest correction (proposal; Exploratory revision 2 matched the intended result in 12/12 cases)
- Treat identifiers as **identifiers, on both sides**: a word from a short list built from the data (form, rule, section, schedule, itr, step, part, para, tier, rev, eps), followed by an optional space or hyphen and digits with an optional letter suffix.
  - Their digits are **removed from the number comparison**.
  - Each identifier in the claim must instead appear in the quote **or in the heading the quote sits under** (`_section_heading`, as the document-kind rule already does).
- Quantities (digits, money, counted number words) are compared exactly as today.
- `_numbers` itself is unchanged; the identifier handling sits in `verify_claims`.

### W3 test matrix (all New `VerifyClaimsTest` cases; "current" and "proposed" columns were executed or simulated as stated)

| ID | Claim vs quote | Expected | Current (Reproduction) | Proposed (Exploratory) |
|---|---|---|---|---|
| A1 | "ITR-1 can be filed when total income does not exceed ₹ 50 lakh during the FY" vs the list item under "ITR-1 can be filed by a Resident Individual whose:" | Keep | **Rejected** | Kept |
| A2 | ITR-2 named, quote contains ITR-2 | Keep | Kept | Kept |
| A3 | ITR-2 claimed under an ITR-1 heading | Reject | Rejected | Rejected |
| A4 | Form 6 named, quote has Form 6 | Keep | Kept | Kept |
| A5 | Form 8 claimed, quote says "Form-8" | Keep | Kept | Kept |
| A6 | Rule 81 / rule 81; the year 1989; "Step 3" | Keep | Kept | Kept |
| B1 | Age 20 ↔ "twenty years" | Keep | Kept | Kept |
| B2 | Rs. 200 ↔ "Rs. 200.00/-" | Keep | Kept | Kept |
| B3 | 14 days ↔ "fourteen days" | Keep | Kept | Kept |
| B4 | 2 copies ↔ "two copies" | Keep | Kept | Kept |
| B5 | 12% ↔ 12% | Keep | Kept | Kept |
| C1 | Form 7 vs Form 6 | Reject | Rejected | Rejected |
| C2 | 18 years vs twenty years | Reject | Rejected | Rejected |
| C3 | Rs. 300 vs Rs. 200 | Reject | Rejected | Rejected |
| C4 | **thirty days vs "fourteen days … Form 30"** | Reject | **Kept (false acceptance)** | Rejected |
| C5 | 10% vs 12% | Reject | Rejected | Rejected |
| C6 | **Form 6A vs Form 6** | Reject | **Kept (false acceptance)** | Rejected |
| C7 | Rule 82 vs rule 81 | Reject | Rejected | Rejected |

**Existing tests that must stay unchanged and passing** (last run passed): `test_numbers_must_equal_the_quoted_numbers`, `test_ages_deadlines_and_counts_in_words_must_equal_the_quoted_ones`, `test_number_words_without_a_unit_are_not_numbers`, and every money, negation, back-reference and document-kind test.

---

## 4. W10 — "Fees as prescribed"

### Where it comes from (Reproduction, `w3c4_w10.txt`)
- The stored text says "Fees as prescribed along with user charges" on pages **23, 24, 25 and 26** only. That is the official wording, correctly extracted. **Extraction is not the problem.**
- On page 26, with the follow-up "And how much does it cost?":
  - **generation** produces "Fees as prescribed along with user charges." (verified, a real quote);
  - **completeness verification** (`check_claims`) returns **`complete=True`**, so `routes.guidance` skips `answer_from_naming_pages`. **This is the root cause.**
  - If completion ran with that elliptical question, `answer_from_naming_pages` would return **all 8 fee rows** of page 27, not just the IDP's. With the explicit question ("What is the fee for an International Driving Permit?") it returns only Rs. 1000. **A second, contributing cause.**

### When the wording is enough
**Never as an amount.** It is an honest *partial* answer only when no approved page states the fee, as with the citizen's duplicate-licence fee (fixture 66 expects an abstention or no amount).

### Possible minimal corrections, not decided
1. A claim whose only content is "as prescribed" never makes an answer complete. This is deterministic, in `routes.guidance` or `rag.check_claims`.
2. When completion runs, the naming-page question includes the procedure's name, so "it" becomes "International Driving Permit".

### W10 test matrix

| ID | Case | Expected | Type |
|---|---|---|---|
| W10-1 | IDP open, "And how much does it cost?" | Rs. 1000 from page 27, or "Fees as prescribed" flagged **partial**; never only page 27's other rows | New (backend, mocked model) + Reproduction (fails today: `complete=True`) |
| W10-2 | "What is the fee for an International Driving Permit?" | Rs. 1000 (unchanged) | Existing evaluation case (answers[7], [68]) |
| W10-3 | Citizen's duplicate-licence fee | No amount; abstain or partial; never the school's Rs. 5000 | Existing (answers[66]; `ApplicantLimitTest`) |
| W10-4 | Renewal page, "How much is the renewal fee?" | Rs. 200 via completion (unchanged) | Existing (answers[67]) |
| W10-5 | A real "fees as prescribed" answer with no naming page (permanent DL "What is the fee?") | Partial, not complete | New |

---

## 5. W11 / W12 — identification threshold and wrong-page similarity

### Facts
`IDENTIFY_MIN_SCORE` 0.53 and `IDENTIFY_MARGIN` 0.03 (`backend/config.py`, lines 40–41), used by `procedure_search.classify` (line 48). **Nothing is to be changed in this stage.**

### Evidence (Exploratory, `w2_w11_sim.txt`; `evidence/investigations/rag_audit/tie_scores.txt` and `probe_staging.jsonl`)
- **In-scope near-misses:**
  - "How much do I pay to get my DL renewed?" 0.518;
  - "I sold my bike. What does the buyer have to do and by when?" 0.529;
  - "How much does a duplicate RC cost?" 0.492.
- **Out-of-scope questions in the same band:** birth certificate 0.519, GST 0.509, "Certificate venum" 0.495, train ticket 0.494.
  - **Lowering the threshold would admit them.** Scores alone cannot separate these groups, so a threshold change is **not supported by evidence**.
- **Out-of-scope questions already above 0.53:**
  - "How do I apply for a marriage certificate?" (0.657) → **matched the TN FAQ page today** (a known miss in the identification sets);
  - "Ayushman Bharat" (0.546) is caught by the name check.
- **Wrong page by similarity:**
  - "How do I get my name on the voters list?" → How to Vote (0.693) over Register to Vote (0.607);
  - "Which form is used to correct entries in the electoral roll?" → ambiguous Overseas 0.615 / Register 0.598 (Form 8 is on Register);
  - "What's the charge to fix my address in Aadhaar at the post office?" → ambiguous 0.693 / 0.670.
- **The RC override** is W2, not a threshold problem.

### W11/W12 test matrix (no fix proposed; these protect any future change)

| ID | Case | Expected | Type |
|---|---|---|---|
| T-1 | The 3 in-scope near-misses | Recorded as known misses; must not become wrong-page matches | Exploratory (current: no_match) |
| T-2 | Out-of-scope: ration card, birth certificate, GST, train ticket, Ayushman Bharat, fishing licence, building permit, company registration | **No match** (must hold under every change) | Existing evaluation cases (answers 72–75, held-out 22) + Exploratory scores |
| T-3 | Marriage certificate | Known false match (page 17); any change must not make more of these | Existing identification sets (MISS) |
| T-4 | Voters list / Form 8 / post-office Aadhaar | Recorded; a later change, if any, must fix them without touching T-2 | Exploratory |
| T-5 | `ClassifyTest`, `IdentifyApiTest` (thresholds and margins) | Unchanged | Existing, last run passed |

---

## 6. Existing tests that must keep passing
- **Backend:** all 209, notably:
  - `ClassifyTest`, `AbbreviatesTest`, `NamesSomethingTest`, `NamedByTheOthersTest`;
  - `IdentifyApiTest` (5 abbreviation and close-call tests);
  - `IdentifyNeedsApiTest`;
  - `VerifyClaimsTest` (money, digits, number words, negation, back-reference, document kind, H1 lead-in);
  - `ApplicantLimitTest`, the guidance API tests.
- **Frontend:** all 61, notably *"follow-ups the open procedure cannot answer"* (3 tests) and *"routes follow-ups to the procedure they name…"*. **One assertion is expected to change under W1** (line 514; see section 1).
- **Evaluations (staging, H1 + number-word baseline):** main 75/80 and held-out 23/27 with 0 incorrect; identification 11/14, 33/42, 30/37, 30/36. The held-out 23 change under W2 is the expected exception (section 2).

## 7. Recommended implementation order
1. **Preserve the Stage 2 evidence** (this plan's temporary scripts) after approval.
2. **W3 revision 2.** It closes a confirmed path for a wrong deadline that survives every verification stage (the Form 30 case), and the ITR-1 false rejection. The change is self-contained in `verify_claims`, with no fixture conflict.
3. **W2.** One condition in `_decide`; held-out 23 is a documented expected change.
4. **W1.** Backend flag plus frontend change plus the test contract change at line 514; needs approval of that assertion change.
5. **W10.** Partial, not complete, for "as prescribed", and the procedure name in the completion question; decide after W1, which also touches follow-ups.
6. **W11/W12:** measurement only; no change without new evidence.

Each step needs: its new tests (positive and negative) failing before and passing after; the full backend and frontend suites; main and held-out; the 4 identification sets; and the audit probe (`evidence/investigations/rag_audit/scripts/probe.py`) compared with the preserved output.

## 8. Risks and regression considerations
- **W1:** an extra `/api/identify` call per follow-up (latency, and an extraction call when `MULTI_HINT` matches). Switching depends on name matching: a follow-up naming a service only loosely (A5) still relies on the old fallback.
- **W2:** depends on name initials. A page whose own abbreviation is not at the start of its initials would lose the override for confident matches only. Close calls are unchanged.
- **W3:** the identifier word list is hand-made from the stored data. An identifier word not on it ("Annexure 2") stays a number, as today. Allowing an identifier from the section heading is a slight loosening, bounded by the heading.
- **W10:** marking "as prescribed" incomplete will trigger completion more often, so it must not pull rows for other services (W10-1).
- **Model variance:** single runs of `qwen3:8b`. Treat a difference of ±1 as noise, and inspect every changed case.
- **Fixture premises:** held-out 23 was written for approved data. Other fixtures may carry similar assumptions; report, never edit.

## 9. Uncertainties
- The exploratory W1 and W2 results replay only parts of the pipeline: W2 `_decide` on whole messages, not the full `identify()` flow with need extraction.
- C4 and the W3 cases use injected or synthetic claims; real generation has not been seen to produce the wrong deadline.
- The Tamil and Romanized versions of these cases were not probed.
- Approved-database behaviour was not probed (pages 15–21, 27, 31–38 differ from staging).
