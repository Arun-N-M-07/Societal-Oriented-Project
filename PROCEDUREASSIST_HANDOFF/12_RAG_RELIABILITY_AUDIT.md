# 12 — RAG reliability audit (Stage 1, 25 Oct 2026)

**Type:** read-only investigation. No application code, test, fixture, database, `.env` or Git state was changed. This file is the only file written.

**Code audited:**
- `backend/rag.py` SHA-256 `2eb8f9ff…` and `tests/test_guidance.py` `97cc1f7b…`: H1 plus the number-word fix, uncommitted, on top of `3491415`;
- backend tests: 209 OK.

**Data:**
- Probes ran on `procedureassist_staging` (26 pages, 140 chunks, unchanged: `8aba737f…`/`93000b69…`).
- The approved database was only read, for comparisons (`016980ee…`/`3e45c78f…`, unchanged).

**Evidence:**
- Scripts and raw outputs are in a temporary session folder (section 11). They are not yet copied into `evidence/`, because this audit could write only this file.
- Every number below comes from those runs, or from evaluation outputs already in `evidence/`.

**Labels:**
- **Confirmed** = reproduced by a run, or proved by reading the code path with a concrete input.
- **Hypothesis** = plausible, but not demonstrated.

---

## Part 1 — The actual execution path

### 1.1 Query processing (`backend/routes.py::identify_procedure`, line 323)
1. **Normalisation** (`routes._normalized` line 288 → `backend/normalize.py::normalize_query`).
   - Runs only for Tamil script, for Romanized-Tamil hint words, or when Tamil is selected (`needs_normalizing`).
   - `qwen3:8b` rewrites the question into one English query, or flags it as needing clarification.
   - English questions are not preprocessed: no spelling fixes, synonyms or expansion.
2. **Generic-question check** (`procedure_search.names_something`, line 72). A question made only of `GENERIC_WORDS` ("How do I renew?") gets a clarification request.
3. **Several needs** (`procedure_search.identify_needs`, line 205).
   - Only if `MULTI_HINT` matches ("and", ",", a second sentence…), `extract_needs` asks `qwen3:8b` for up to `MAX_NEEDS` = 3 needs, each with a phrase and a standalone question.
   - Several *services* produce a "multiple" result. Several questions about *one* service stay in the single flow (the prompt says so).
4. **Identification** (`procedure_search.identify`, line 154 → `_decide`, line 129).
   - `rank_procedures` (line 76): each page's score is the cosine similarity of its best chunk. Only the top `MAX_CANDIDATES` = 3 pages are returned.
   - `classify` (line 48): **matched** if exactly one page scores ≥ `IDENTIFY_MIN_SCORE` 0.53 and is within `IDENTIFY_MARGIN` 0.03 of the best; ambiguous if several are; otherwise no_match.
   - Then four overrides, in order:
     - an abbreviation that names exactly one nearby page wins (lines 131–141);
     - otherwise a term used by only one page wins, if that page is nearby;
     - the capitalised-name check (`mentions`);
     - the named-page tie rule (`named_by_the_others`).
   - If extraction found exactly one need, its phrase, its standalone question and the whole message are each tried in turn (line 154).
5. **Follow-ups** (frontend `CitizenPage.tsx::handleSend`, line 248; `answerFollowUp`, line 162).
   - With a procedure open, the follow-up text alone goes to `/api/guidance` for **that** page.
   - Only if the answer is `insufficient_evidence` is the follow-up identified again and answered elsewhere.
   - **No earlier conversation is sent to the backend.** The open page is the only context.

### 1.2 Retrieval (`rag.retrieve`, line 149)
- `qwen3-embedding:0.6b`, 1024 dimensions. Queries get `QUERY_INSTRUCTION`; documents don't (`embed_texts`, line 104).
- `ORDER BY cosine_distance LIMIT GUIDANCE_PASSAGES` (5), filtered to the chosen `procedure_id`.
- No full-text search, no threshold inside the page, no reranking, no metadata other than the procedure (searching for `tsvector`/`ts_rank` finds nothing).
- **Structural fact (confirmed): 20 of 26 staging pages have ≤ 5 chunks**, so on those pages retrieval returns the whole page. Ranking inside a page matters only on pages 16 (19 chunks), 33 (17), 39 (12), 18 (11), 31 (8), 15 (7) and 30 (7).

### 1.3 Context assembly (`rag._passages`, line 174; `build_guidance_prompt`, line 178)
- Chunks are listed in similarity order as `--- PASSAGE <chunk id> ---` blocks.
- No neighbouring chunks are added and nothing is deduplicated or reordered.
- `LLM_CONTEXT_TOKENS` = 32,768. Five chunks are about 5 KB, so **no truncation happens** (confirmed: the largest prompts observed were about 6–7 KB).
- Chunks repeat a short last paragraph, or start at a heading (`chunk_text`, line 69). A quote must come from **one** passage.

### 1.4 Generation (`rag._answer`, line 421; `_ask`, line 435; `extractor.call_qwen`)
- `qwen3:8b` via Ollama: `temperature: 0`, `format: json`, `think: false`.
- One call per question returns `{"insufficient_evidence", "claims": [{"text", "quote", "chunk_id"}]}`.
- The prompt asks for short claims, steps in official order, amounts with their purpose, conditions kept, nothing about other services or applicant types, partial answers allowed, and abstention otherwise.
- There is **no** decomposition into sub-questions, and no per-aspect retrieval.

### 1.5 Verification (`rag.verify_claims`, line 313, deterministic; then `check_claims`, line 445, model)
1. **Deterministic checks.** The quote must:
   - be in the cited retrieved chunk, word for word;
   - have at least 4 words or be a whole list item;
   - share every number in the claim, including counted number words (`COUNTED`, line 252);
   - keep every money amount of its sentence or row;
   - agree on negation;
   - not open with a back-reference;
   - name the same kind of document (`_document_kinds` / `_section_heading`).

   Duplicate claims are dropped.
2. **Model check.** `check_claims` re-reads the surviving claims for meaning and completeness. `_for_the_asker` (line 464) drops fees limited to an organisation.
3. **Completion.** `routes.guidance` (line 363): if the answer is incomplete, `answer_from_naming_pages` (line 354) tries a page that names the procedure, such as the fee table.

---

## Part 2 — Strengths to keep

| Strength | Evidence |
|---|---|
| **Retrieval inside the chosen page is reliable** | Every English fixture case with an expected page and evidence pattern: the evidence chunk is in the top 5 in **81/81** cases. All 42 audit probes: the evidence chunk was within the top 5 of the expected page in every case where it exists (worst rank 5: "I sold my bike…", page 30). |
| **Direct questions find the right page** | Probe group P (transport-age paraphrases): 7/7 correct page. Group B (questions on the large, untested pages): 10/12. Group M (multi-part): 4/4. |
| **The verification layer prevents wrong answers** | Main 75/80, held-out 23/27, **0 incorrect**. The H4 work showed the exact-quote, money, back-reference and document-kind rules each rejecting real wrong claims. The number-word fix now rejects wrong ages and deadlines (5/5 injected cases). |
| **Follow-ups on the open page work for elliptical questions** | "What about a transport vehicle?" (page 22) and "And if I apply late?" (page 24) were both answered with the right evidence. |
| **Nothing is lost to the context window** | 5 chunks in a 32k context |
| **Simple, inspectable design** | About 5,000 lines; every rule is tested; the evaluation script names the failing stage |

---

## Part 3 — Confirmed weaknesses

Ranked by severity. "Probe" refers to the 42-question audit probe (Part 11).

### W1. A follow-up about another procedure is answered from the open page, producing a misattributed claim. **Severity: High (a wrong fact reached the answer).**
- **Where:** `frontend/src/CitizenPage.tsx::answerFollowUp` (line 162) asks the open page first and re-identifies only on abstention. `rag.check_claims` (line 445) is the only remaining guard.
- **Evidence:** with the EPF page (36) open, "What about EPS?" returned *"Employees below ₹15,000 per month (mandatory) are covered under **EPS**."* The quote is the **EPF** page's own coverage line. Identifying the follow-up on its own scores EPS (37) first (0.535).
- **Why it happens:** the EPF page mentions EPS, so it doesn't abstain. The model then attributes an EPF fact to EPS, and the meaning check accepts it. The document-kind rule covers certificate, licence, permit and card only, not schemes.
- **Recommended action:** before answering on the open page, identify the follow-up. If it **confidently names a different procedure** (an abbreviation or explicit name match, as `_decide` already detects), answer from that page. Otherwise keep today's order. Test with "What about EPS?" on EPF and "And how much does it cost?" on IDP (which must stay on IDP).

### W2. The abbreviation rule overrides a clear vector match. **Severity: Medium–High (wrong page; the citizen gets "fee as per Rule 81" instead of the amount).**
- **Where:** `procedure_search._decide`, lines 131–141 (`if len(named) == 1: status, ids = "matched", named` runs even when `classify` already matched another page).
- **Evidence:** "What is the fee to renew the RC of a motorcycle?"
  - `classify` → matched page 39 (0.654; the next page is 0.539).
  - "RC" abbreviates *Renewal of **V**ehicle **R**egistration **C**ertificate* (initials RVRC), so the rule switched to page 28 (0.530).
  - The answer was "Pay appropriate fee as specified in Rule 81…" (partial). The Rs. 300 row on page 39 was never consulted.
- **Related:** `abbreviates` matches initials as **substrings**: "DL" matches *Employees' Deposit Linked Insurance (EDLI)*, and "RC" matches *REV-101 Community Certificate*.
- **Recommended action:** apply the abbreviation decision only when `classify` did not return a confident match, or when the named page is within the margin of the best score. One condition; test both directions (EPS and DL close calls must still resolve).
- **Documentation discrepancy:** `10_PENDING_WORK.md` H3 attributes the motorcycle fee miss to retrieval ("the right row is not retrieved"). For this wording the cause is identification (W2); the evidence row ranks 1st within page 39. The original H3 wording reached page 39 and abstained, so H3 has two mechanisms.

### W3. Digits inside names are checked as numbers, rejecting correct claims about ITR-1, ITR-2, Form 6A and similar. **Severity: Medium (safe, but large coverage loss on the two largest pages).**
- **Where:** `rag._numbers` (line 203) reads "ITR-1" as the number 1. `verify_claims` requires `_numbers(claim) ⊆ _numbers(quote) ∪ money`.
- **Evidence:** "What is the income limit for filing ITR-1?" The model claimed *"The income limit for filing ITR-1 is ₹ 50 lakh during the FY."* quoting *"Total income does not exceed ₹ 50 lakh during the FY"*. It was rejected: claim numbers {1, 50}, quote {50}. The page was right and the evidence ranked 1st, but the answer was an abstention. "Can I use ITR-1 if I have capital gains?" also abstained (not traced).
- **Why the evaluation never showed it:** no fixture case covers pages 33 or 16 (W7).
- **Recommended action (needs its own review):** don't treat a number as a constraint when it is part of an identifier token (letters-hyphen-digits, such as `ITR-1`) that also appears in the question or the procedure name. Form numbers that differ ("Form 7" against a quote about Form 6) must still be rejected. Positive and negative tests required.
- The same claim's second quote was rejected by the negation rule ("does not exceed" vs "limit is"). That's strict but intended; not recommended for change.

### W4. A fee from one table row is presented as the fee for another purpose. **Severity: Medium.**
- **Where:** `verify_claims` checks quote, number and money, but not *what the fee is for*. `check_claims` accepted it.
- **Evidence:** "What is the fitness test fee for a motorcycle?"
  - The claim citing item 10 (test fee: manual Rs. 200, **automated Rs. 400**) was correctly rejected by the money rule.
  - The same claim also cited item 11, the *grant or renewal of certificate of fitness*, Rs. 200, and **was kept**. The result was "The fitness test fee for a motorcycle is Rupees Two Hundred Only" (flagged partial), citing the certificate fee.
- **Recommended action:** investigate before fixing; no single small rule is obvious. Record it as a known risk of the meaning check, alongside the 3/3 failures already documented.

### W5. The model abstains on answerable questions that need light inference or a colloquial reading. **Severity: Medium (safe).**
- **Evidence (traced; the evidence chunk was rank 1 and the model returned `insufficient_evidence: true`):**
  - "How much does my boss put into my PF?" ("boss" = employer);
  - "I am 19. Can I get a licence to drive a lorry?" (it would need "20 is the minimum");
  - "For a passport, what documents do I need, what is the fee and how do I apply?" (the steps exist; the fee doesn't).
- Untraced but likely the same: "Can a 19-year-old obtain this licence?" (abstained); "Can I apply at 20?" and "Am I eligible for a commercial driving licence?" both returned only the 18-year non-transport rule (partial).
- **Cause:** generation, a limit of the 8B model. The prompt already says to answer the part that can be answered.
- **Recommended action:** no verification change. Optional: one prompt sentence allowing "state the official rule that decides the citizen's case", measured on the full sets. A larger model is the structural fix (hardware decision).

### W6. Multi-part questions about one procedure get one 5-chunk retrieval and one all-or-nothing answer. **Severity: Medium.**
- **Where:** `identify_needs` keeps a single service in the single flow by design; `rag._answer` is one call.
- **Evidence (probe group M):**
  - permanent DL (2-chunk page): 3 claims, complete;
  - EPF: 2 claims;
  - **passport: abstained** (W5);
  - **ITR-1 (17 chunks): 1 claim, "Who can file ITR-1", a heading presented as a fact** that passed both checks.
- **Recommended action:** add multi-part cases to a new probe set first (W7). Consider decomposition only if those cases show retrieval, not generation, losing evidence. In this audit, retrieval didn't lose it (evidence rank ≤ 2 in all four).

### W7. Evaluation coverage misses the pages and question types where the system is weakest. **Severity: High for measurement.**
- **Evidence:** pages 33 (ITR-1, 17 chunks), 16 (ITR-2, 19), 39 (Rule 81 fees, 12), 32 and 17 have **zero** fixture cases; page 18 (11) has one.
- The sets also have no multi-part question about one procedure, no follow-up about a *different* procedure, and few colloquial rewordings.
- W1, W2 and W3 are all invisible to the current 107 questions.
- **Recommended action:** create a **new, separate** probe fixture (existing fixtures stay frozen), with the owner's approval of the questions, before any change is scored.

### W8. The chunker splits long paragraphs mid-sentence. **Severity: Low–Medium.**
- **Where:** `rag.chunk_text` (line 69) splits a paragraph longer than 1,000 characters at a space.
- **Evidence:** 5 real mid-sentence cuts on staging:
  - page 15, chunks 12/13;
  - page 19, chunks 146/147 and 147/148;
  - page 30, chunks 77/78 ("Central Motor | Vehicle Rules 1989");
  - page 40, chunks 585/586 (the APY contribution sentence).

  A sentence cut this way can't be quoted whole, because a quote must lie in one passage.
- **Recommended action:** split oversized paragraphs at sentence ends first. This changes chunks, so it needs re-embedding and belongs with the data migration (`07`), not before it.

### W9. Stored-text defects that block exact quotes. **Severity: Low–Medium (data).**
- **Evidence:**
  - Page 30 stores "the owner **ofa** motor vehicle dies" in both databases. The model writes "of a", so the three-month legal-heir sentence was rejected ("My dad passed away…", "What if the owner died?" → partial). Whether the live page has the typo is **unverified**.
  - Page 30 also joins headings to their bodies ("Transfer of ownership on death of owner of the vehicle Apply in Form 31 …"), so a heading and its first sentence form one paragraph.
- **Recommended action:** check during the migration review of page 30. Never correct official text by script.

### W10. "Fees as prescribed" can be judged a complete answer, so completion is skipped. **Severity: Low–Medium.**
- **Evidence:** "And how much does it cost?" as a follow-up on the IDP page returned "Fees as prescribed along with user charges." (not flagged partial). The fee table's Rs. 1000 was never consulted. The fixture's explicit wording ("What is the fee for an International Driving Permit?") passes.
- **Cause:** `check_claims` returned `complete=true`. `answer_from_naming_pages` runs only when incomplete.
- **Recommended action:** a deterministic "a claim saying only 'as prescribed' is not complete" check would be small. Measure it first.

### W11. Thresholds turn some in-scope colloquial questions into "no match". **Severity: Low–Medium.**
- **Evidence:** "How much do I pay to get my DL renewed?" (best 0.518), "I sold my bike. What does the buyer have to do and by when?" (0.529), "How much does a duplicate RC cost?" (0.492). All are below 0.53 with the right page first.
- **Hypothesis:** lowering the threshold would recover these but could match out-of-scope questions (ration card, GST, train tickets must stay no_match).
- **Recommended action:** measure with `scripts/evaluate_identification.py` and an out-of-scope list before changing anything.

### W12. Embedding similarity picks a related but wrong page. **Severity: Medium.**
- **Evidence:**
  - "How do I get my name on the voters list?" → How to Vote (0.693) over Register to Vote (0.607). It answered "verify your name on the list…", a different need, and wasn't flagged partial.
  - "Which form is used to correct entries in the electoral roll?" (held-out) → ambiguous: Overseas scores highest (0.615); Register to Vote, which holds Form 8, scores 0.598.
  - "What's the charge to fix my address in Aadhaar at the post office?" → ambiguous 0.693/0.670, although "post office" decides it.
  - "I work in Dubai. Can I vote in India?" → Register to Vote, although Overseas scored highest (0.555 vs 0.533). The exact route wasn't traced; it is probably the extracted-need phrase.
- **Recommended action:** see Part 8. A narrow lexical tie-breaker is the only candidate with evidence; it needs measurement.

---

## Part 4 — Potential weaknesses (need testing)

| Risk | Status |
|---|---|
| The same number in different units ("three days" vs "three months") is accepted | Known limitation of the number check (documented with the number-word fix) |
| Bare counts ("six sections" vs "five") are not checked | Known limitation |
| Run-to-run variance of the meaning check | Seen in history (3/3 failures). Not re-measured here. |
| Tamil and Romanized wordings of the probe questions | Not probed in this audit (Tamil sets: 30/36 identification) |
| Approved-database behaviour of the probe | Only staging was probed. Pages 22, 24–26, 28–30 and 34 are identical in both; others differ. |
| Long fee table: the right row outside the top 5 for some wordings (original H3) | Not reproduced with this audit's wordings (rank 1). Still open for the original H3 wording. |
| Relation and comparison answers (`/api/relation`) | Not probed in this audit |

---

## Part 5 — Retrieval assessment

- **Query processing.** Adequate for English; Tamil is handled by normalisation. No expansion. Colloquial words ("boss", "bike", "lorry") rarely broke **retrieval**. They broke identification (W11, W12) or generation (W5).
- **Identification is the main point of failure.**
  - Probe: **30/37** non-follow-up questions reached the expected page.
  - The 7 misses: 3 no_match below the threshold (W11), 1 abbreviation override (W2), 2 wrong page by similarity (W12), 1 close call (W12).
  - The remaining evaluation failures are also identification close calls: learner vs permanent (0.631/0.628), "I live abroad" (0.647/0.627), "I just turned 18" (phrase-path disagreement), Form 8 (0.615/0.598), and the grace-period fee (0.688/0.661, then completion abstains).
- **Retrieval inside the page is not the weak point.** 81/81 fixture cases and all probes have the evidence within the top 5.
- **Answer to the transport-licence question.** All 7 rewordings found page 22, and chunk 347 ranked 1st every time. **Retrieval succeeded for every rewording.** The differences were in generation: 3 answered with the 20-year rule, 2 answered only the 18-year rule, and 2 abstained.
- **Metadata filtering** (the procedure filter) removed no useful evidence. Every evidence chunk was on the chosen page whenever the page was right.
- **Context assembly** loses nothing to truncation. Its only measurable effect is that a sentence cut across two chunks can't be quoted (W8).

## Part 6 — Generation and verification assessment

- **Correct page, evidence retrieved:** 19 of the 30 probe questions on the right page produced a claim citing the evidence.
- **The other 11:**
  - 6 abstentions (W5, W3);
  - 5 partial or off-target answers, including one wrong-row fee (W4), one source typo (W9) and one heading-as-claim (W6).
- **Misleading output seen:**
  - W1 (EPS), the clearest;
  - W4 (fee purpose);
  - W12 (wrong need answered).

  None appears in the 107 evaluation questions, which is why they still report 0 incorrect.
- **Verification is doing its job.** Every rejection traced in this audit was correct by its rule: inexact quote, digit in a name, dropped money, negation. The exceptions are the over-strict digit-in-name case (W3) and the meaning check's misses (W1, W4, W10).
- **Recommendation:** none of the rules should be loosened.

## Part 7 — Ingestion and chunking assessment

- **Kept well:**
  - headings: 40 of 114 later chunks start at a heading, and 50 repeat the previous paragraph;
  - fee rows with their parent row (page 39 sub-rows carry "4. Issue or renewal…");
  - FAQ questions (after the 23 Oct scraper fix, staging only);
  - source URL per page.
- **Weak:**
  - 24 later chunks start mid-section; most are self-describing fee rows, 5 are true mid-sentence cuts (W8);
  - one typo and joined heading-body paragraphs on page 30 (W9);
  - no PDF support (documented source gaps: UIDAI list, APY chart);
  - approved data still lacks the 23 Oct scraper fixes (the migration is pending, `07`).
- **No structural loss of tables or numbered lists was found** on staging.

---

## Part 8 — The ten techniques assessed

| # | Technique | Already present? | Evidence of need | Smallest version | Downsides and risk | Verdict |
|---|---|---|---|---|---|---|
| 1 | Hybrid vector + full-text retrieval | No | **None inside a page** (81/81). Some for identification (W12, "post office"). | A lexical tie-breaker in `_decide` for close calls only | A second ranking path; weights to tune | **Later, only if** W12 cases persist after the cheaper fixes |
| 2 | Query expansion | Only Tamil normalisation | Weak: colloquial misses were mostly generation (W5) | — | An extra model call per question | **Not recommended** |
| 3 | Intent extraction | Yes (`extract_needs`, `normalize`) | — | — | — | Keep |
| 4 | Metadata-aware retrieval | Procedure filter only | None | — | — | **Not recommended** |
| 5 | Reranking | No | None inside pages | — | Latency; another model | **Not recommended** |
| 6 | Parent-child / neighbouring chunks | No | Only W8 (5 cut sentences) | A sentence-aware split (W8) instead | Re-embedding | Fix the chunker instead (with the migration) |
| 7 | Better context assembly | Basic | Only W8 | — | — | Covered by W8 |
| 8 | Multi-part decomposition | Services only, not aspects | Some (W6), mostly generation | Measure first (W7) | More calls; partial-answer logic | **Defer** until W7 data exists |
| 9 | Follow-up resolution | Open-page-first only | **Yes (W1, a wrong fact; W10)** | Identify the follow-up and switch only on a confident different-procedure match | Could move follow-ups away from the open page; must be tested both ways | **Recommended** |
| 10 | Confidence calibration | Fixed thresholds | Some (W11), plus W2 | Measure the threshold with an out-of-scope list; fix W2's override | Out-of-scope false matches | W2: **recommended**. Threshold: **measure only** |

---

## Part 9 — Prioritised plan and order

| Order | Change | Impact | Evidence | Complexity | Regression risk | Depends on |
|---|---|---|---|---|---|---|
| 1 | **Audit probe fixture**: a new, separate set covering pages 33, 16, 39, 18 and 32, colloquial rewordings, multi-part questions and cross-procedure follow-ups. Existing fixtures untouched. | High (measurement) | W7 | Low (data file, owner-approved questions) | None | Owner approval of the questions |
| 2 | **W2**: the abbreviation rule must not override a confident match | Medium–High | Confirmed (RC case) | ~1 condition plus tests | Low; check the EPS, DL and VVPAT cases | 1 (to measure) |
| 3 | **W1**: follow-up routing to a confidently named different procedure | High (removes a wrong-fact path) | Confirmed (EPS) | Small (frontend `answerFollowUp`, maybe a flag from `/api/identify`) | Medium: must keep "And how much does it cost?" on the open page | 1, 2 |
| 4 | **W3**: identifier digits ("ITR-1") not treated as numeric constraints when they also appear in the question or name | Medium (ITR coverage) | Confirmed (ITR-1 limit) | Small (`_numbers` / `verify_claims`) | Medium: form-number mismatches must still be rejected | 1 |
| 5 | **W10**: a claim that says only "as prescribed" doesn't make an answer complete | Low–Medium | Confirmed (IDP follow-up) | Small | Low | 1 |
| 6 | **W11**: threshold measurement (no change unless the out-of-scope list stays clean) | Low–Medium | Confirmed near-misses | Measurement only | — | 1 |
| 7 | **W8 and W9** with the data migration: sentence-aware split of long paragraphs; page 30 review | Low–Medium | Confirmed | Small code plus re-embedding | Changes chunks; needs migration approval | `07` migration |
| — | W4, W5, W6 | Medium | Confirmed | Unclear / model-bound | — | Re-assess after 1–5 |

Each step is one small change with its own positive and negative tests, a full backend run, both evaluation sets, the identification sets and the new probe set. Unchanged verification rules are a precondition for every step.

## Part 10 — Acceptance criteria for Stage 1 improvements

1. **No regression:**
   - main ≥ 75/80 and held-out ≥ 23/27, with **0 incorrect**;
   - identification sets ≥ 11/14, 33/42, 30/37, 30/36;
   - all backend tests pass (209 + new).
2. **Verification unchanged:**
   - exact-quote, money, negation, back-reference, document-kind and number rules keep all their existing tests;
   - no rule is loosened to raise a score.
3. **The new probe set (frozen before the first change):**
   - **0 misattributed or wrong-row claims;** W1 and W4 cases answer correctly or abstain;
   - **page identification ≥ 34/37** on its single-procedure questions (today 30/37);
   - the RC-motorcycle question reaches page 39 (W2);
   - the ITR-1 income-limit question is answered with ₹50 lakh (W3);
   - "What about EPS?" on the EPF page answers from EPS or abstains (W1);
   - "And how much does it cost?" on IDP gives Rs. 1000 or is flagged partial (W10).
4. **Out-of-scope safety:** every current out-of-scope and "not stated" case still gives no match or an abstention.
5. **Each change** is recorded in `10`, `05` and `11`, with before/after evidence in `evidence/`.

---

## Part 11 — Evidence (temporary session folder)

Folder: `/private/tmp/claude-501/-Users-arunnm-Projects-SOP/bebaf14e-7bdf-4da2-8b3f-9c2a6edb540d/scratchpad/audit/`.

| File | Contents |
|---|---|
| `recall.py`, `recall_staging.txt` | Within-page evidence rank for 81 fixture cases |
| `probe.py`, `probe_staging.jsonl` | The 42-question audit probe: identification, top-3 scores, evidence rank, claims. Exit 0. |
| `miss_traces.txt` | Stage-by-stage traces of six misses (uses `evidence/investigations/h4/scripts/trace_h4.py`) |
| `chunk_context.txt` | Heading context and mid-sentence cuts for all chunks |
| `tie_scores.txt` | Scores behind the remaining close calls |

**These are temporary and may disappear after a reboot.** They should be copied into `evidence/investigations/rag_audit/` once the owner approves writing there. Earlier evidence used here: `evidence/evaluations/h1_fix/`, `evidence/investigations/h4/`, `evidence/investigations/number_words/`.

## Part 12 — Documentation discrepancies found

- **`10_PENDING_WORK.md` H3:** the cause is given as retrieval only. One wording fails at identification (W2).
- **`10_PENDING_WORK.md` H4:** the Tamil voter-helpline example is a generation abstention, not an inexact quote (already accepted by the owner, not yet corrected).
- **`10_PENDING_WORK.md` M3:** it suggests a deterministic temperature, but `call_qwen` already uses `temperature: 0`.
- **`03_AI_AND_RAG_LOGIC.md` §2.2(4):** it describes the abbreviation rule correctly, but not that it can override a confident match (W2).

## Part 13 — Overall assessment

**The architecture is fundamentally sound and does not need redesign.**
- Retrieval inside a page is reliable.
- Verification blocks wrong facts and must stay as it is.
- The weaknesses sit at three boundaries:
  - identification heuristics and thresholds (W2, W11, W12);
  - follow-up routing (W1);
  - the 8B model's generation and meaning check (W4, W5, W10).
- Evaluation coverage (W7) hides the first two.

The recommended work is a handful of small, separately testable changes, measured on a new probe set, not new retrieval machinery.
