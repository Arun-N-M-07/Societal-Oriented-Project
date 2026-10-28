# 18 — Complete system reliability audit (25 Oct 2026)

**Type:** read-only audit. No application code, test, fixture, database, `.env`, threshold or Git state was changed.

**Code audited:** the working tree on top of `3491415`: H1, number words, W3, W1, W10 and H3 are in; W2 is withdrawn. Backend 221 tests and frontend 63 tests passed at 16:40 today.

**Data:** approved `procedureassist` (24 pages, 122 chunks) and `procedureassist_staging` (26/140); checksums unchanged.

**New evidence:** `evidence/investigations/system_audit/` (`citizen_outcomes.py` with outputs for both databases). Everything else cited is existing evidence.

**Labels:**
- **[C] Confirmed:** measured or read in code.
- **[L] Likely:** strong indirect evidence.
- **[H] Hypothesis.**
- **[U] Unverified risk.**

---

## 1. Executive summary
- **The architecture is fundamentally sound** [C]. Only official, human-approved text is evidence. Retrieval inside a page is reliable (81/81 fixture cases; the page-39 row-group case was fixed by H3). A deterministic verifier blocks most wrong facts. No redesign is needed.
- **Citizens can still receive confidently wrong guidance today** [C], for three reasons, verified against today's code (`system_audit/citizen_outcomes_*.txt`):
  1. **Defective stored data on the live (approved) database.** "Can apprentices become EPF members?" gets "Apprentices **can** become EPF members" (officially **No**). The TN income-certificate question gets a document from another certificate's list. Staging answers both correctly, but **the migration hasn't happened**.
  2. **Identification has no notion of scope.** "How do I renew my driving licence **in the UK**?" gets 3 claims about **Indian** renewal, not flagged partial. "US passport" gets Indian Passport Seva steps. "Marriage certificate" shows the card *"REV-101 Community Certificate"* with **CAN-editing steps** (page 17's known wrong name and steps, in both databases).
  3. **Verification is lexical, not semantic.** It proves a quote exists and its numbers, money, negation, document kind and identifiers match. It can't prove that the claim's *subject* (which service, category, condition or need) is what the quote is about. The model's meaning check is the only guard there, and it has failed repeatedly (§4, RC3).
- **The weaknesses are systemic, not isolated bugs.** Most of the 20+ individual findings since 23 Oct trace back to **seven root causes** (§4). Several were patched one by one with deterministic rules; the rules work, but the classes remain.
- **The evaluation sets can't see the confirmed wrong answers.** "0 incorrect" on 75/80 and 23/27 coexists with the live EPF/TN errors and the UK/US answers. **Measurement is the first fix.**
- **Shortest sensible path to production** (§10):
  1. a frozen safety regression set;
  2. deterministic scope checks at identification;
  3. the reviewed data migration (with page 17 corrected);
  4. a re-baseline;
  5. a condition-preservation rule;
  6. operational basics (logging, a retry, timeouts, deployment hardening).

## 2. Architecture (as implemented)

| Layer | Code | Role |
|---|---|---|
| Ingestion | `scraper.validate_url` / `fetch_static_html` / `fetch_rendered_html` / `clean_html` (`_is_block`, `_row_context`, `is_menu`); `extractor.extract_procedure` (`qwen3:8b`, JSON) + Pydantic `ProcedureExtraction`; `routes.create_extraction` / `re_extract_procedure` / `save_procedure` (HMAC provenance token, `build_chunks`, one transaction) | URL → text → draft → human review → saved, and immediately live |
| Data | `models.Procedure`, `ProcedureChunk` (`content`, `embedding vector(1024)`, `chunk_index`); `rag.chunk_text` (about 1,000 characters, heading-aware start) | Evidence = `source_text` chunks; card = reviewed `name`/`summary`/`structured_data` |
| Query understanding | `normalize.normalize_query` (Tamil only); `procedure_search.names_something`, `identify_needs` / `extract_needs` (`qwen3:8b`) | English is used as typed; Tamil becomes an English query; several services are split |
| Identification | `procedure_search.rank_procedures` (best-chunk cosine, top 3) → `classify` (0.53 / margin 0.03) → abbreviation rule → `mentions` → `named_by_the_others`; `names_procedure` → `named` | matched / ambiguous / no match / multiple / clarification |
| Retrieval | `rag.retrieve` (top 5 by cosine in the page) + `_item_continuation` (H3) | Evidence chunks |
| Generation | `rag.build_guidance_prompt`, `_answer` → `extractor.call_qwen` (temperature 0, `format: json`, `think: false`, `num_ctx` 32768, 60 s timeout, no retry, no seed) | Claims, each with quote and chunk ID |
| Verification | `rag.verify_claims` (exact quote, length, numbers excluding identifiers, number words, money per row, negation, back-reference, document kind with RC/DL for amounts, identifiers, duplicates) → `check_claims` (model meaning check + `_for_the_asker`) → `_checked_answer` (fee needs an amount) → `answer_from_naming_pages` (rows naming the procedure) | Final claims, `partial`, `insufficient_evidence` |
| Conversation | `CitizenPage.answerFollowUp` (identify first; switch only to a `named` procedure; else the open page, then a matched page); `followUp` (multi-need) | No history beyond the open procedure |
| Frontend | `CitizenPage.tsx` (card, claims with quotes and links, partial note, refusal, errors with retry, voice, read-aloud), `AdminPage.tsx` | — |
| Operations | `start.sh` / `run.sh` (local only), `/health/ready` | No logging, no deployment |

## 3. Component findings

### A. Ingestion
- **[C] Content can be silently omitted.** The 23 Oct audit found FAQ questions, eligibility cards and fee rows lost (`06`). The scraper is fixed (div/span/summary text, one paragraph per table row, `_row_context`), but **the approved data was scraped before the fix**. PDFs are unsupported (documented gaps).
- **[C] Human review is the only content gate.** It failed for page 17 (the name and steps don't match the page) and was skipped for staging (built by script; `07`).
- **[C] Saved means live** (`routes.save_procedure`). There is no "approved but unpublished" state; also in `14` §14.4. Only `save_procedure` and `delete_procedure` write citizen data; `rag.backfill` adds missing chunks only.
- **[C] No government-domain allow-list** (`validate_url` checks scheme, credentials, localhost and public address only; also `14` §14.5). An admin could approve a non-government page.
- **[C] The card shows reviewed but unverified content.** Answers come from `source_text`; the card's steps and eligibility come from the model's draft as edited by the reviewer (`14` §14.3). Page 17's card shows CAN-editing steps under a Community Certificate name.
- **[C] Provenance:** the HMAC token ties the saved text to the scraped text; `source_url` is unique; claims carry chunk IDs and links.

### B. Data representation
- **[C] Chunks carry only `content`, `embedding` and `chunk_index`.** Heading, section, table and row relationships exist only *inside the text* (row prefixes, heading-aware chunk starts).
- **[C] Mid-sentence chunk splits:** 5 on staging (pages 15, 19, 30, 40; `rag_audit/chunk_context.txt`).
- **[C] Source-text defects:** the page 30 typo "ofa", and headings joined to bodies.
- **[C] Approved and staging are isolated:** separate databases; the app reads one `DATABASE_URL`.

### C. Query understanding
- **[C] English isn't normalised.** Abbreviations (DL, RC, PF) and colloquial words ("bike", "boss") reach the embedding as typed. W11's four threshold misses are all of this kind (`16`).
- **[C] No scope or intent fields** (jurisdiction, document type, action) are extracted from the question. Scope is left to embedding similarity and heuristics (§4 RC2).
- **[C] Multi-part questions about one procedure** go through one retrieval and one generation, all or nothing (`12` W6: passport multi-part abstained).
- **[C] Tamil normalisation runs on the model**, and its "single flow" count varied 21 → 22 between identical runs (`evaluations/h3_fix/needs_staging_tamil*`).

### D. Identification
- **[C] Retrieval keeps the right page:** it's always among the 3 candidates (158/158 distinct in-scope questions on staging, 156/156 on approved; `16`).
- **[C] 0.53 is appropriate.** In-scope near-misses score 0.445–0.529 and out-of-scope questions 0.465–0.525; 0.51 gains 2 and adds 1 false match on each database (`16` §5). **Keep it.**
- **[C] Confident false matches (5 distinct, 0.575–0.687)** — not touched by the threshold:

  | Question | Matched page | Why |
  |---|---|---|
  | US passport | Passport | — |
  | UK driving licence | DL renewal | Also `named=True` |
  | Marriage certificate | TN FAQ (page 17) | — |
  | Change the name on my PAN card | Link PAN with Aadhaar | **The abbreviation rule overrode the top page**: "PAN" is literal in the name. This corrects `16` §4, which said e-Filing registration. |

  `mentions` ignores 2-letter capitals ("US", "UK").
- **[C] Name-check false negatives** ("Indian", "Bengaluru", "Dubai"). The first two are rescued by need extraction; "Dubai" ends on the wrong page.
- **[C] The heuristics interact:** the abbreviation override (RC → page 28, PAN → page 31) against legitimate overrides (PF → EPF); W2 was withdrawn because no principled separator was found (`10`, `11` #20).

### E. Retrieval
- **[C] Reliable within the chosen page:** evidence in the top 5 for 81/81 fixture cases and every Stage 1 probe question.
- **[C] One exception: long fee tables.** Fixed by `_item_continuation` (2/137 retrievals changed; 0 on approved).
- **[C] No truncation:** 5–9 chunks in a 32k context.

### F. Generation
- **[C] Wrong-row choice on near-identical rows:**
  - over-20-years instead of row 4(b);
  - the fitness certificate (item 11) instead of the fitness test (item 10);
  - before the fixes, "RC … Rs. 200" from the fitness row.
- **[C] Exact-quote errors:** "The applicant" vs "An applicant" (H4).
- **[C] Abstaining on answerable or light-inference questions:** "boss", "I am 19 … lorry", passport multi-part.
- **[C] Off-target but true claims:**
  - "voters list" answers how to *check* your name rather than how to enrol;
  - "US passport" gets Indian steps;
  - the UK licence gets Indian renewal rules.
- **[C] Invention is blocked deterministically.** No unsupported claim survived the 107-question sets; every claim needs a verbatim quote.
- **[C] Settings:** temperature 0, no seed. The same inputs gave identical outputs across 3 runs in every H3 case.

### G. Verification
- **Correct claims rejected (safe misses):**
  - inexact quotes;
  - lead-ins worded differently;
  - repeated list items resolving to their first occurrence;
  - "two or three years" read as only 3;
  - an unrelated chunk's identifier;
  - Tamil voter helpline (generation, not verification).
- **Wrong claims that can pass** [C unless marked]:

  | Case | Check that lets it through |
  |---|---|
  | Subject misattribution: a fact about one service or category labelled as another (fitness test fee ← certificate row) | Meaning check only |
  | A condition dropped (over-20-years fee without "older than 20 years") | Meaning check only |
  | The same number in different units ("three days" vs "three months") | Meaning check only |
  | Bare counts ("six sections" vs "five") | Meaning check only |
  | A claim answering a different need or jurisdiction than asked | Nothing checks claim against question |

- **[C] Citations always point at real text** in a retrieved chunk of the cited page (`verify_claims`; the evaluation's citation check). "Supports the claim" is guaranteed lexically, not semantically.
- **[C] Assembly:** `routes.guidance` adds completion claims with their own page ID and link; `partial` is set when not complete. No gap was found between verification and the response.

### H. Conversations
- **[C] W1 fixed:** 17/17 follow-up scenarios pass. **W2 withdrawn:** `_decide` is unchanged since its withdrawal.
- **[C] No history except the open procedure.** Pronoun follow-ups ("And how much does it cost?") work because the page is fixed, and W10 limits completion to the procedure's own rows.
- **[L] Multi-turn context beyond one hop** ("and for my wife?") isn't supported.

### I. Frontend
- **[C] Accurate states:** refusal text, partial note, omitted-claims count, errors with retry, "searched as" for Tamil, clarification and choose screens.
- **[C] A misleading card on false matches:** the procedure card appears on every match, even when the answer abstains (marriage certificate → page 17 card).
- **[C] A down backend shows the login screen** on the admin side (`14` §14.10).
- **[U] Real-speech accuracy** (only synthetic voices tested).

### J. Operations
- **[C] No logging or metrics:** no logger in `backend/`. Failures and slow requests leave no trace.
- **[C] No retries for Ollama** (`call_qwen`, `embed_texts`); 60 s timeouts.
- **[C] The embedding failure:** 2 of 16,859 `/api/embed` calls in Ollama's log returned **400** (25 Oct 12:29:05 and 16:59:29). Both were ~200-text batches from my audit scripts; both succeeded when retried with the same input. The log shows no reason; the cause is unknown. **No single-question citizen embedding is known to have failed.**
- **[C] The laptop slept mid-evaluation** (25 Oct): the run stalled about 2 hours but produced valid output; prevented with `caffeinate`.
- **[C] A guidance request can make 2–4 model calls, plus identify and extraction calls on follow-ups.** Median latency 4–6 s, maximum 46–56 s on the laptop (`evaluations/h3_fix/*`).
- **[U]:**
  - concurrency (a read-only database session is held during model calls; `14` §14.7);
  - no rate limiting;
  - sessions can't be revoked;
  - DNS rebinding;
  - IPv6 binding (`14` §14.12).
- **No deployment artefacts:** `run.sh` reinstalls packages on every start (`14` §14.13).

## 4. Root causes

| # | Root cause | Evidence | Components | Examples | Severity | Systemic? | Correction |
|---|---|---|---|---|---|---|---|
| **RC1** | **Evidence quality: the stored text is wrong or incomplete, and review can fail** | `06`; `citizen_outcomes_approved.txt`; page 17 | Ingestion, data, review | EPF apprentices (live, wrong); TN lists (live, wrong); page 17 name and steps; missing Rule 81 / PFRDA on approved; PDF gaps | **Critical** | Systemic (data) | The reviewed migration (`07`), with page 17 corrected; keep the human gate |
| **RC2** | **Identification has no scope model.** Embedding similarity plus case heuristics decide; jurisdiction, document type and action aren't checked | `16`; `citizen_outcomes_staging.txt` | `procedure_search` | UK licence and US passport answered with Indian rules; marriage certificate → page 17; PAN name change → Link PAN; Dubai → wrong page; the RC/PAN override vs PF | **Critical** (wrong-jurisdiction guidance) | **Systemic** | Deterministic scope checks reusing existing helpers (§9 P0-2) |
| **RC3** | **Verification can't bind a claim's subject to its evidence or to the question** | H3/H4 traces; `12` W1/W4/W12 | `verify_claims`, `check_claims` | EPS ← EPF (fixed by W1); fitness test ← certificate; RC ← fitness fee (fixed for amounts); over-20 condition drop (open); a different need answered | High | **Systemic**; each class needs a rule | Condition-preservation rule (P1-2); claim–question scope covered by RC2's fix; accept the rest as a model limit |
| **RC4** | **Structure lost in text and chunks:** relationships live only in prose | `06`, `rag_audit/chunk_context.txt`, H3 | Scraper, chunker, data model | FAQ loss (approved); table cells (approved); item-4 rows (fixed); mid-sentence splits (5); page 30 headings | Medium–high | Systemic, mostly fixed in code; data pending | Migration (re-scraped text); sentence-aware splitting at the same time (P1-5) |
| **RC5** | **Limits of the 8B model** | H4, H3, `12` W5/W6 | Generation, meaning check | Inexact quotes; wrong rows; needless abstentions; multi-part all-or-nothing; meaning check 3/3 failures | Medium (verification makes it safe, costs coverage) | Systemic | Keep verification; a model choice is a hardware decision (P2) |
| **RC6** | **Evaluation blind spots:** fixtures are tied to approved data, single runs, no answer-level safety checks | §7 | `fixtures/`, `scripts/evaluate_*` | "0 incorrect" alongside the live EPF/TN errors and UK/US answers; held-out 23's premise | **Critical for decisions** | Systemic | Frozen safety regression set with forbidden and required patterns (P0-1) |
| **RC7** | **No operational safety net** | §3 J | Backend, scripts | No logs; no retry; laptop sleep; 400 errors; no deployment | Medium now; **critical before production** | Systemic | Logging, one retry, timeouts, deployment hardening (P3) |

## 5. Known failure inventory (current status)

| Failure | Root cause | Status |
|---|---|---|
| EPF apprentices "can join" (approved) | RC1 | **Open (live)**; fixed by migration |
| TN income list mixed (approved) | RC1 | **Open (live)**; fixed by migration |
| Page 17 name and steps shown on the card (both DBs) | RC1 | **Open** |
| UK licence renewal → Indian rules | RC2 | **Open** |
| US passport → Indian steps | RC2 | **Open** |
| Marriage certificate → page 17 card | RC2 | **Open** (answer abstains) |
| PAN name change → Link PAN card | RC2 | **Open** (answer abstains) |
| "Dubai" → wrong voter page | RC2 | **Open** |
| "Voters list" → How to Vote (W12) | RC2 / RC3 | **Open** |
| RC fee questions with the abbreviation → "Rule 81" partial (W2) | RC2 / RC4 | Open, safe |
| Over-20-years fee could pass without its condition | RC3 | Open (not observed) |
| Fitness test fee ← certificate fee (partial) | RC3 / RC5 | Open |
| 4 W11 threshold misses | RC2 (phrasing) | Open, safe (no match) |
| Inexact quotes, abstentions, multi-part (H4, W5, W6) | RC5 | Open, safe |
| Identifier, number-word, fee-completeness and follow-up classes (W3, number words, W10, W1, H1, H3) | — | **Fixed** (tests and evaluations) |

## 6. Reliability metrics and existing baselines

| Metric | Baseline (source) | Limitation |
|---|---|---|
| Identification, in scope (distinct questions, whole message) | Staging: 138/158 correct matches, 8 asks, 5 "wrong page" (3 by design: tie rule plus fee-table completion), 7 misses, of which 4 are threshold misses in the real API (`16`) | Need extraction replayed only for failures |
| Identification sets | 11/14, 33/42, 30/37, 30/36 (`05`) | Message level only |
| Out-of-scope rejection | 16/21 distinct questions not matched (5 false matches) on both DBs (`16`) | Small set; few jurisdiction cases |
| Retrieval recall@5 (within the page) | 81/81 fixture cases; all probe questions (`rag_audit`) | The large pages are barely in the fixtures |
| End-to-end (evaluation definition) | Staging 75/80, 23/27; approved 74/80, 24/27; "incorrect" 0 (`05`) | **Blind to the confirmed wrong answers** (§7) |
| Abstention / clarification | Staging main: 8 appropriate abstentions, 1 missed answer, 4 unnecessary clarifications; held-out: 3, 1, 2 | Not judged on clarification quality |
| Numerical accuracy (deterministic) | Number-word and identifier injected cases: all wrong ones rejected (`number_words/`, W3 tests) | Synthetic cases |
| Latency | Median 4–6 s, maximum 46–56 s (`h3_fix/*`) | Laptop, single user |
| Failure handling | Unit tests (`test_health`, 502 paths); 2/16,859 embedding 400s in the log | No live outage drill |

**Can't be measured today (missing data or instrumentation):**
- claim-level semantic support rate;
- condition-preservation rate;
- citation accuracy beyond "the quote exists";
- clarification correctness;
- Tamil *answer* quality;
- latency and error rates in use (no logs);
- behaviour under concurrency;
- user acceptance of suggestions.

## 7. Missing evaluation coverage

| Category | Covered by | Gap |
|---|---|---|
| Normal questions | answers 01–09 (34), held-out | — |
| Colloquial / paraphrase | answers 15 (4), population B (8), audit probe V group | Few colloquial **English** answer cases |
| Abbreviations | tamil 08, a few answer cases (DL, RC, EPS) | No answer-level abbreviation set; the W11 misses aren't in fixtures |
| Multi-part (one procedure) | **None** | Missing |
| Cross-procedure follow-ups | **None in fixtures** (`rag_fixes/followup_scenarios.py`, 17 scenarios) | Not frozen as a fixture |
| Ambiguous | answers 17, held-out ambiguous, population E | — |
| Out of scope | answers 18 (4), population G (9), identification unsupported (8) | Only identification is checked for jurisdiction; **no answer-level jurisdiction cases** |
| Fees / numbers / tables | answers 02/08 (page 27), held-out fees | Page 39 (Rule 81) has **no fixture**; the H3 matrix isn't frozen |
| Eligibility / conditions | answers 03/09, held-out `claim` pattern (1) | Condition preservation measured once |
| Document lists | answers 04, held-out documents | — |
| Tamil | answers 12–14 (12), held-out (3), tamil.json (36) | Answer quality in Tamil isn't judged (answers are English) |
| Missing / contradictory evidence | answers 19 (3), held-out not stated (2) | EDLI contradiction not a fixture |
| **Known wrong answers** (EPF apprentices, TN income, UK/US, page 17 card) | **None** | Why "0 incorrect" misleads |
| Model / database failures | Unit tests only | No live drill |

## 8. Critical risks
1. **Live wrong answers until the migration** (RC1).
2. **Wrong-jurisdiction guidance** presented as an answer (RC2): a citizen abroad following Indian rules.
3. **A misleading card on false matches** (RC1 + RC2).
4. **Scores that look safe while known errors exist** (RC6), leading to wrong release decisions.
5. **No observability** (RC7): production errors would be invisible.

## 9. Prioritised roadmap

### P0 — critical correctness and safety

| ID | Root cause | Change (minimal) | Files / functions | Benefit | Regression risk | Tests | Depends on | Complexity |
|---|---|---|---|---|---|---|---|---|
| **P0-1** | RC6 | **Frozen safety regression set:** every confirmed failure in §5, with *forbidden* patterns (e.g. "can become EPF members", Indian rules for a UK question) and, where the official text answers, *required* patterns. Expectations come from the official text and need your approval. | New fixture + `scripts/evaluate_answers.py` (reuse the `claim`/`evidence`/`answer` keys) | Makes the real risks measurable | None (measurement) | Run on both DBs | Your approval of expectations | Small |
| **P0-2** | RC2 | **Deterministic scope checks at identification, reusing existing helpers:** (a) `mentions` also checks 2-letter capitals that aren't any procedure's abbreviation (`abbreviates`), so "US"/"UK" must appear on the page; (b) a document kind named in the question (`rag._document_kinds`, e.g. "marriage certificate") must appear in the page text. Otherwise no match. | `procedure_search.mentions` / `_decide` | Removes the confirmed US/UK/marriage false matches **[H, to be measured]** | DL/RC/PF/EPS questions; questions naming a document the page uses differently; must run all sets | Unit + P0-1 set + all evaluations | P0-1 | Small–medium |
| **P0-3** | RC1/RC4 | **Reviewed data migration** (`07`, including the pre-migration check), with page 17 renamed and its steps corrected (superseded 27 Oct: the owner decided to delete page 17; see `19`) | Admin workflow, no code | Fixes the live EPF/TN errors and the page-17 card | Live page drift; reviewer error | `07` validation list + P0-1 set | Your approval; reviewer time | Medium (people) |

### P1 — core reliability
- **P1-1 (RC3):** condition-preservation rule. An age, period or count condition (`COUNTED`, or digits with a unit) in the quoted *row or sentence* must appear in the claim, mirroring the money rule in `verify_claims`. This closes the over-20-years gap. Risk: new missed answers when the model summarises; measure. Small.
- **P1-2 (RC2):** the abbreviation override. Revisit the `_decide` override (RC → 28, PAN → 31) with a measured rule, only after P0-1 and P0-2; W2 depends on it. Medium.
- **P1-3 (RC2/C):** option E from `16` ("Did you mean…?" for scores 0.45–0.53), your UX decision. Small.
- **P1-4 (RC1):** no card without an answer on a weak match. Hypothesis: when guidance abstains *and* the match wasn't `named`, show the abstention without the procedure card. `CitizenPage`. Small. Needs a UX decision.
- **P1-5 (RC4):** sentence-aware splitting of long paragraphs in `rag.chunk_text`, plus the page-30 text review. **It changes chunks, so it must be done with P0-3** (re-embedding). Small code, migration-bound.

### P2 — coverage and robustness
- Multi-part answering for one procedure (`12` W6): measure with the P0-1 set first. Medium.
- Spelling out DL/RC in English queries (`16` C): only together with P1-2. Small.
- Fitness test vs certificate (W4) and other near-identical rows: a model limit; revisit with a model upgrade. —
- Tamil answer quality and normalisation variance: measure. Medium.
- A larger local model (RC5): hardware decision; measure on all sets. —

### P3 — performance, operations, maintainability
- **Structured logging** of request ID, stage, timings and failures (no question text, for privacy). `routes.py`, `rag.py`. Small.
- **One retry for transient Ollama failures** in `embed_texts` and `call_qwen`. Small.
- **Request timeouts in the frontend;** don't hold the database session during model calls (`14` §14.6/7). Small–medium.
- **Deployment hardening:** HTTPS, rate limiting, session revocation, a government-domain allow-list for ingestion, reproducible installs (`14` §14.5, §14.13, README). Medium.
- **Documentation drift:** the H3 and W11 documents are dated "26 Oct" but were written on **25 Oct** (`00`, `03`, `04`, `05`, `10`, `11`, `16`); `16` §4 PAN wording (see §3 D). Small.

## 10. Recommended order
1. **P0-1** safety set (measure first; no behaviour change).
2. **P0-2** scope checks, measured on P0-1 and all sets.
3. **P0-3** migration, with **P1-5** at the same time (one re-embedding).
4. Re-baseline everything.
5. **P1-1** condition rule.
6. **P3** logging and retry (before any public use).
7. **P1-2 / P1-3 / P1-4** decisions.
8. **P2** as capacity allows.

**Production gate:** P0-1, P0-2, P0-3, P1-1, P3 logging, retry and timeouts, and deployment hardening.

## 11. What should not be changed
- The **verification rules** (exact quote; numbers with identifiers excluded; number words; money per row; negation; back-reference; document kind with RC/DL for amounts; applicant limit; fee completeness). Every one blocks a confirmed wrong-answer class.
- The **0.53 threshold** (`16`).
- **W1, W3, W10, H1, H3** (measured, no regressions).
- **The human approval workflow and provenance token.**
- **Local-only models and the PostgreSQL/pgvector design.**
- **Retrieval architecture.** No reranker, hybrid search or query expansion: no evidence of need beyond H3, already fixed.
- **The heading-aware chunker rule.**
- **Frozen fixtures** (add new sets; never edit existing ones).

## 12. Remaining uncertainties
- **[H]** Whether P0-2's two checks remove the false matches without new misses: needs measurement.
- **[U]** The cause of the two embedding 400 errors.
- **[U]** Concurrency and connection-pool behaviour under several users.
- **[U]** Real-speech recognition quality.
- **[U]** IPv6 binding and the non-ASCII cookie edge (`14`).
- **[U]** Live-page drift since 23 Oct (the pre-migration check addresses this).
- **[L]** That other unlisted out-of-scope or jurisdiction questions behave like the UK/US cases (only 2 such cases were tested end to end).
- The audit probes and citizen-outcome checks are **single runs** (temperature 0 gave identical repeats in every H3 case).
