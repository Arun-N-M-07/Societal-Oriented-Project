# 16 — W11: identification threshold investigation (25 Oct 2026)

**Type:** read-only investigation. No application code, test, fixture, database, `.env`, threshold or Git state was changed.

**Evidence:** `evidence/investigations/w11/`. All three scripts are read-only, use embeddings only (except the final real-API check), and were run on both databases:
- `w11_eval.py` and `w11_eval_<db>.txt`;
- `w11_analysis.py` and `w11_analysis_<db>.txt`;
- `w11_options.py` and `w11_options_<db>.txt`.

**Labels:** **Confirmed** = measured. **Hypothesis** = not measured.

**Code state:** the current working tree. The identification code has not changed since the RAG reliability fixes; W2 is withdrawn.

---

## 1. Executive summary
- **A correction to the brief.** The three cited examples (birth certificate 0.519, GST 0.509, train 0.494) are **out-of-scope questions**: fixture cases `answers[74–76]`, category "18 outside", `expected: [None]`. No approved page covers them, and rejecting them is **correct**. Stage 2 (`15`, §5) cited them as the reason *not* to lower the threshold.
- **The real W11 false negatives are 4 distinct in-scope questions** (confirmed on the real `/api/identify`):

  | Question | Best page | Score | Database |
  |---|---|---|---|
  | "sold my bike, need to transfer the RC" | Transfer of Vehicle Ownership | 0.445 | both |
  | "How much does a duplicate RC cost?" | Rule 81 page | 0.492 | staging |
  | "How much do I pay to get my DL renewed?" | Renewal of DL | 0.518 | both |
  | "I sold my bike. What does the buyer have to do and by when?" | Transfer | 0.529 | both |

  All are colloquial ("bike") or abbreviated ("DL", "RC").
- **The correct page is never missing from retrieval** (confirmed). In 158 distinct in-scope questions on staging and 156 on approved data, the expected page is **always among the 3 candidates**, ranked 1st in about 93%. These 4 questions are rejected by the threshold, not lost by retrieval.
- **0.53 is appropriate** (confirmed). Relevant and irrelevant scores overlap: in-scope misses score 0.445–0.529; out-of-scope questions score 0.465–0.525. No threshold improves both sides. The best alternative, 0.51, recovers 2 questions and adds 1 false match on each database.
- **The larger identification risk isn't the threshold.** 5 distinct out-of-scope questions are **confidently false-matched at 0.575–0.687**: "US passport", "UK driving licence", "change the name on my PAN card", and "marriage certificate" (2 phrasings). No threshold below 0.69 would remove them.
- **Recommendation:**
  - keep 0.53;
  - adopt no threshold, margin or ranking change;
  - consider only option E (offer the best page as a choice for scores 0.45–0.53), as **your user-experience decision**;
  - investigate the high-score false matches separately.

## 2. How identification works today (code)
`routes.identify_procedure` runs these steps:
1. **Normalisation**, for Tamil or Romanized Tamil only (`normalize.py`). English questions are not changed; DL/RC are expanded only for Tamil.
2. **`names_something`**: a question made only of generic words gets a clarification.
3. **`identify_needs`**: if `MULTI_HINT` matches, the model extracts needs. With one need, its phrase and standalone question are tried before the whole message (`identify`).
4. **`_decide`**, for each text:
   - `rank_procedures`: the best-chunk cosine per page, **top 3 only**;
   - `classify`: matched if exactly one page scores ≥ `IDENTIFY_MIN_SCORE` 0.53 and is within `IDENTIFY_MARGIN` 0.03 of the best; ambiguous if several; otherwise no match;
   - then four overrides in order: the abbreviation rule (≥ `ACRONYM_MIN_SCORE` 0.45), the single-page term rule, the name check (`mentions`), and the named-page tie rule.
5. **Response:** matched, ambiguous (the citizen chooses), no match, or clarification.

## 3. Root causes of the false negatives (confirmed)

| Question | Today (real API) | Why |
|---|---|---|
| "How much do I pay to get my DL renewed?" | no match | Best score 0.518 < 0.53. "DL" names four pages, so the abbreviation rule can't decide. Written as "driving licence", the score is 0.677. |
| "I sold my bike. What does the buyer have to do and by when?" | no match | Best score 0.529 (0.001 below). "bike" and "buyer" are not the page's wording (transfer of ownership). |
| "sold my bike, need to transfer the RC" | no match | 0.445, below even the abbreviation floor (0.45). |
| "How much does a duplicate RC cost?" (staging) | no match | 0.492. "RC" abbreviates page 28, but page 28 isn't in the top 3, so the rule can't use it. Written in full, the score is 0.610. |

**Name-check misses (confirmed, a different cause).** On the whole message, the `mentions` check rejects "My **Indian** passport has expired…" (0.649), "…I live in **Bengaluru**" (0.621) and "I work in **Dubai**…" (0.555): a capitalised word in the question is missing from the page. The docstring documents this weakness. In the real API, need extraction rescues the first two. **"Dubai" ends on the wrong page** (Register to Vote rather than Overseas Voters).

**Not caused by:** normalisation (these questions are English and never normalised); retrieval (the page is always in the candidate set); ranking (the right page is 1st in all 4).

## 4. False positives (confirmed)

| Question (out of scope) | Matched page | Score | Why the threshold can't help |
|---|---|---|---|
| How do I apply for a **US** passport? | Passport | 0.687 | Very similar text; `mentions` ignores 2-letter capitals ("US"), so the country is never checked |
| How do I renew my driving licence in the **UK**? | DL renewal | 0.660 | Same ("UK") |
| How do I get / apply for a marriage certificate? | TN e-Sevai FAQ (page 17) | 0.625–0.657 | The FAQ lists many certificates; no capitalised name to check |
| How do I change the name on my PAN card? | Link PAN with Aadhaar (corrected in `18`: e-Filing registration ranks first at 0.575, but the abbreviation rule overrides it because "PAN" is written in Link PAN with Aadhaar's name) | 0.575 (top page) | "PAN" appears on both pages |

Below the threshold (correctly rejected), on one or both databases:
- birth certificate 0.519 / 0.482;
- TN ration card 0.525 (approved);
- GST 0.509 / 0.506;
- Ayushman Bharat 0.502;
- train 0.494;
- stolen passport police report 0.465.

## 5. Score distribution and threshold trade-off (confirmed; distinct questions)
- **In-scope expected-page scores below 0.53:** 0.445–0.529 (the misses), and 0.475–0.514 for questions matched today by other rules (abbreviation, need extraction).
- **Out-of-scope best scores:**
  - below the threshold: 0.465–0.525;
  - above it: 0.575–0.687, the 5 false matches.

| Threshold | Staging: correct / missed / false matches | Approved: correct / missed / false matches |
|---|---|---|
| 0.45 | 139 / 4 / 8 | 136 / 4 / 8 |
| 0.50 | 139 / 5 / 6 | 137 / 4 / 6 |
| **0.51** | **140 / 5 / 6** | **138 / 4 / 6** |
| 0.52 | 139 / 6 / 5 | 137 / 5 / 6 |
| **0.53 (today)** | **138 / 7 / 5** | **136 / 6 / 5** |
| 0.55 | 137 / 8 / 5 | 135 / 7 / 5 |
| 0.60 | 129 / 16 / 5 | 130 / 14 / 4 |

These counts are on the whole message, without need extraction, so the misses include the name-check cases that need extraction rescues in the real flow. Lowering the threshold trades each recovered question for an out-of-scope match: at 0.51, +2 correct and +1 false match on each database.

## 6. Evaluation set
- **Sources (all existing, with their labels):**
  - `answers.json` and `heldout.json` (non-follow-up, English);
  - `population.json` and `demo_services.json` (single-need);
  - `identification.json`, where the labelled page is in the database;
  - the Stage 1 audit probe (`evidence/investigations/rag_audit/probe_staging.jsonl`).
- **Size:** 206 cases on staging and 204 on approved; 184 and 182 distinct questions.
- **No new labelled cases were invented.** The only additions are the DL/RC spelled-out variants (option C), which are labelled as such and inherit their original question's label.
- **Per-question results:** expected page, its rank and score, the top two pages and scores, the decision and the verdict are in `w11_eval_<db>.txt`. The real-API outcome for every case not correct today is in `w11_analysis_<db>.txt`.

## 7. The five approaches

| Approach | Evidence | Verdict |
|---|---|---|
| **A. Threshold** | No value separates the classes (§5); 0.51 recovers 2 and adds 1 false match | **Keep 0.53** |
| **B. Top-two margin** | With a gap under 0.02 the top page is wrong about half the time; from 0.02 up it's right about 95%. The existing margin already makes close calls ambiguous. Extending it to second candidates below the threshold changed **1** question, a correct match turned into "choose" | **No change** |
| **C. Query normalisation (spell out DL/RC in English)** | Scores rise 0.12–0.16. Gains: "DL renewed", "duplicate RC" (staging). Losses: "sold my bike … RC" turns from a safe no match into a **wrong page** (the "(RC)" token triggers the abbreviation rule); "I lost my DL" turns from correct to "choose". Interacts with the withdrawn W2. | **Not recommended alone**; revisit with W2 |
| **D. Ranking** | The right page is always in the top 3, and 1st in all 4 misses | **No change** |
| **E. Clarification: offer the best page when 0.45 ≤ best < 0.53** | Offers the **right** page for all 3 recoverable misses (DL renewed, sold bike, duplicate RC). Offers an **unrelated** page for 4 out-of-scope questions on staging and 6 on approved. Nothing is matched automatically. Reuses the existing `ACRONYM_MIN_SCORE` (0.45); no new number. | **Possible, your decision** |

## 8. Recommendation
1. **Keep `IDENTIFY_MIN_SCORE` at 0.53** (confirmed by both sweeps).
2. **Adopt no margin, ranking or normalisation change now** (B, C, D).
3. **Option E is the only change with net evidence,** and it needs your decision. It recovers the colloquial and abbreviated near-misses with the citizen's confirmation, at the cost of showing an unrelated suggestion for some out-of-scope questions.
   - **Implementation sketch (not built):** in `classify` or `_decide`, a best score in [0.45, 0.53) returns "ambiguous" with that one candidate; the citizen page already shows candidates to choose from.
4. **Investigate the high-score false matches separately.** They are the larger safety issue and no threshold reaches them. Two directions to check, both hypotheses:
   - `mentions` ignoring 2-letter country codes ("US", "UK");
   - broad certificate pages such as the TN FAQ attracting any certificate question.

## 9. Risks
- **E:**
  - irrelevant suggestions for out-of-scope questions in the band;
  - a citizen might accept a wrong suggestion (the page shown would then answer only from its own text, and verification still applies);
  - more "choose" screens.
- **Lowering the threshold:** confirmed new false matches (§5).
- **C:** confirmed wrong-page and needless-choice cases (§7); an interaction with the abbreviation rule.

## 10. Regression tests required before any implementation
**Identification:**
- The 4 misses: expected behaviour under E is that the right page is offered and not auto-matched.
- Every out-of-scope fixture case (answers 72–76, held-out 22, population and demo-services "none" cases, identification "unsupported" cases): never matched. Under E, also record which get a suggestion.
- The 5 high-score false matches: recorded; must not increase.
- The existing close calls (learner/permanent, overseas/general, Aadhaar UIDAI/post office, Form 8): still ask.
- Abbreviation cases (EPS, EPF, PF, DL early, RC renew, VVPAT): unchanged.
- `ClassifyTest` and `IdentifyApiTest`: unchanged.

**End to end:**
- both answer sets on both databases;
- the 4 identification sets;
- the follow-up scenarios (W1 depends on `/api/identify`: an offered candidate must not set `named`);
- the audit probe.

## 11. Open questions
- **Need extraction was replayed only for the cases that aren't correct today** (real API). The sweep uses the whole message.
- **Tamil and Romanized questions were not swept.** Their normaliser already expands DL/RC.
- **Would citizens accept a wrong suggestion under E?** That needs user testing, not measurement.
- **The high-score false matches** (§4, §8.4).
- **A transient embedding error.** The approved-database run failed once with "embedding service unavailable" (HTTP 400 from Ollama) and succeeded on retry, as happened once on 25 Oct. Cause unknown.
