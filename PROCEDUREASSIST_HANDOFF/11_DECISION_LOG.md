# 11 — Decision log

Each entry gives the decision, the evidence behind it and the alternatives that were rejected. All decisions date from October 2026. Entries 1–31 are 23–25 Oct; **entries 32–58 (26–28 Oct) are at the end, as full records.**

## Rejected approaches: do not repeat without new evidence
| Approach | Measured result | Entry |
|---|---|---|
| Lowering the identification threshold (0.53) or margin (0.03) | Near misses (0.492–0.529) overlap out-of-scope questions (0.494–0.519); it would match birth certificate, GST, train tickets | 21, 36 |
| A model (LLM) check of the chosen procedure | Removed all 8 confident false matches but rejected 20 correct identifications (157 → 137 of 216) | 38 |
| Score gating of matches | False matches score 0.524–0.657; the correct matches it would reject score 0.475–0.811 | 38 |
| Spelling out "RC"/"DL" for the search | Broke 6 other questions (IDP, VVPAT, learner's licence…) | 39 |
| An answer-prompt sentence about the citizen's own facts (for the overseas abstentions) | Fixed neither abstention; changed 5 of 16 other answers | 40 |
| "The whole message's page wins" instead of a choice | +2–4 correct, but +1 false match on each database | 41 |
| A document-type check against page text (marriage certificate) | Lost 5–16 correct matches | 25 |
| Repeating headings on every later chunk; a loose heading rule | Attached stale headings to unrelated sections; treated list items as headings | 9, 10 |
| Lowering `is_menu` to 2 repeats | Removed real content | 11 |
| A model-based applicant classifier; trusting the model's meaning check alone | Approved wrong claims 3/3 on the same input | 2, 7 |
| W2 abbreviation override change | Off-target fees, because the right fee rows were not retrieved; broke the PF near-tie | 20 |
| Re-extract / re-scrape feature in the admin page | **Removed** at the owner's request | 32 |
| Replacing page 17 with a renamed card | **Superseded:** the owner deleted the page | 48 |
| Direct SQL or script writes of staging text into the approved database | Never allowed: it bypasses human review | 13, 53 |
| Approving N1 (Instant e-PAN) as it stands | A lost/duplicate PAN question can reach a verified answer that the page contradicts | 57 |

| # | Decision | Evidence / reason | Rejected alternatives |
|---|---|---|---|
| 1 | Every answer claim must quote the approved page word for word; code verifies quotes, numbers, amounts and negation. | The 8B model paraphrases and occasionally changes amounts or meaning. | Trusting the model's own judgement alone. |
| 2 | Applicant-type limits are checked in code (`APPLICANT_LIMIT`), not by the model. | The model labelled the "licence to a school or establishment" fee row as applying to anyone, 3 times out of 3. | A model-based applicant classifier (built, measured, removed). |
| 3 | A claim must carry every amount of money in the sentence or table row its quote comes from. | The model claimed "an additional fee of Rs. 300" after the grace period, dropping the Rs. 1,000 a year; the meaning check approved it. | A whole-paragraph version: it rejected EDLI's correct "Minimum benefit: ₹2.5 lakh" because the paragraph also states other amounts. Narrowed to sentence level. |
| 4 | Clarify rather than guess when two procedures score within 0.03. | Close scores between related services, e.g. learner's vs permanent licence. | Always taking the top score. |
| 5 | Named-page tie rule: in a close call, pick the page every other candidate merely names, if the question uses that page's whole name. | IDP fee, "Who can join APY?" and the Romanized renewal fee asked for a needless choice on staging. Completion from the naming page already answers the fee. | Preferring fee pages for fee questions: a keyword rule, and brittle. |
| 6 | Quotes may not open with a back-reference ("In such cases…"). | "In such cases a fee of Rs. 30/- will be realised" was shown as *the* renewal fee, losing its condition (more than 30 days late). | Relying on the meaning check. |
| 7 | The document kind a claim names must appear in its quote or the quote's section question. | On staging the model reported the trade-certificate motorcycle fee (Rs. 500) as the registration-certificate renewal fee; the meaning check approved it 3/3. | Relying on the meaning check; prompt wording. |
| 8 | The scraper keeps text held directly in `div`, `span` and `summary` tags, and one paragraph per table row. | EPFO lost all 27 FAQ questions and its eligibility cards. Bare "Yes/No" answers produced a wrong apprentice answer. Tamil Nadu lost the certificate name above each document list, so documents were taken from the wrong list. | Leaving extraction as it was and tuning prompts. |
| 9 | Fee sub-rows carry their numbered parent row (`_row_context`). | Rule 81 fee schedule rows such as "(b) Motor cycle Rupees Three Hundred Only" said nothing about what they are for. | **Repeating the last heading on every later chunk** (built, reverted): it attached "(c) Three wheeler…:", "4. Bank Details:" and "Who It Covers?" to unrelated sections. |
| 10 | Chunks start at a question or lead-in ending in "?" or ":" when its section so far is short. | A chunk boundary split the polling-booth steps, so answers skipped "First polling official…". | **A loose heading rule** (short line, no digits): it treated list items such as "Photo" and "Valid mobile number" as headings. |
| 11 | Income-tax manuals are proposed at their `?mobile-app=1` address. | The same official page without the site menus; a paragraph-by-paragraph diff showed nothing lost. The 2-repeat "Company" menu is not caught by `is_menu`. | **Lowering the `is_menu` threshold to 2 repeats**: it would have removed real content (a Tamil Nadu document line, the PAN–AO delinking text). |
| 12 | Gaps are recorded, not filled from unofficial sites. Covers passport fees, the PAN–Aadhaar fee amount, the APY contribution chart, the Aadhaar address-proof list (PDF) and the citizen duplicate-licence fee. | Only first-party government pages count as evidence. Bank and third-party sites were found but not used. | Adding bank/aggregator pages. |
| 13 | All data changes are rehearsed in `procedureassist_staging`. The approved database changes only after owner approval, through the admin review workflow, with a backup first. | Approved records are the citizen-facing evidence; deleting before replacements are ready would leave procedures without evidence. | Updating approved records directly from scripts. |
| 14 | PFRDA's APY page is added alongside India Post's, not instead of it. | PFRDA adds the income-tax-payer exclusion and pension slabs. India Post adds where to open the account and the debit schedule. | Replacing India Post's page. |
| 15 | Evaluation fixtures and expected answers are never changed to raise scores. Clarifications and abstentions are not counted as correct answers. | Honest measurement. | — |
| 16 | A colon-less lead-in ("…in the following circumstances") gives a quote its document kind **only when no "?"/":" heading is above it** (H1, 24 Oct). The change is in `_section_heading`, not `_is_heading`. | Page 25's three circumstances were falsely rejected. A fallback can only turn `""` into a heading, so no answer can be newly rejected; it changed 9 blocks of page 25 and nothing else. | "Nearest lead-in wins": it would re-parent staging page 17's CAN steps from question 6 to "…has the following advantages". Changing `_is_heading`: it would change chunking and stale the stored chunks. Adding "as follows" and other forms: no stored page uses them. |
| 17 | Form, rule and return numbers ("ITR-1", "Form 30", "Form 6A", "rule 81") are identifiers, not quantities: left out of the number check, and compared as names against the quote or its heading (W3, 25 Oct). | "ITR-1" made a correct claim fail. "Form 30" made "thirty days" pass against "fourteen days" (surviving the meaning check 3/3). "Form 6A" passed as "Form 6". | Exempting identifier digits only when the identifier is somewhere in the passage: it fixed ITR-1 but missed the Form 30 and Form 6A cases. Loosening the number rule. |
| 18 | A follow-up moves to another procedure only when it **names** it: its own abbreviation, or every word of its name (W1, 25 Oct). `/api/identify` reports `named`; the page identifies first. | "What about EPS?" on EPF was answered with an EPF fact presented as EPS, because the open page did not abstain. | Switching whenever the follow-up matches another page: "What about the certificate?" matched an unrelated TN FAQ. A guard inside `/api/guidance`: it would fire on 16/92 fixture cases (fee-table answers name other services). |
| 19 | A fee question is complete only with an amount or "free", and fee-table completion keeps only rows that name the procedure (W10, 25 Oct). | The model called "Fees as prescribed" complete; a vague follow-up got all 8 fee rows. | Trusting the model's completeness judgement. Adding the procedure name to the question (less direct than filtering rows). |
| 20 | **W2 withdrawn**: the abbreviation override stays as it was until H3 (row retrieval on long fee tables) is fixed (25 Oct). | With W2, RC fee questions reached the right page (39) but its RC rows are not retrieved (rank 9 of 12), so citizens got the fitness-certificate or over-20-years fee instead of "fee as per Rule 81" (partial). W2 also broke the PF near-tie. | Keeping W2 and accepting off-target fees; adding a margin condition (fixes PF, not the off-target fees). |
| 21 | The identification threshold stays at 0.53, and held-out fixture 23 is not changed (25 Oct). | Scores of in-scope near-misses (0.492–0.529) and out-of-scope questions (0.494–0.519) overlap. Fixture 23's abstention is still right for the approved data, and with W2 withdrawn it is right on staging too. | Lowering the threshold; editing the fixture for staging. |
| 22 | A retrieved chunk that ends with a numbered table item brings the following chunks of exactly that item, when the question uses at least two words of the item's label (H3, 25 Oct). | The RC renewal rows (item 4) ranked 8th–11th of 12; with them in context the motorcycle question gets Rs. 300. Without the relevance check, a chunk ending with item 10 pushed row 9(b) out of the hypothecation answer (3/3). | Whole page as context (worse answers for some questions); vehicle-class keyword matching (the class words occur in five items); more passages for every question. |
| 23 | "RC" and "DL" are read as registration certificate and driving licence when a claim states an amount (25 Oct). | The model presented the fitness-certificate fee as the RC renewal fee (passed every check). Spelling out every claim rejected 8 of 9 correct RC document-list claims, where RC names the procedure. | Spelling out every claim; a question-level document check (it would reject document lists). |
| 24 | A permanent safety set (`fixtures/evaluation/safety.json`) holds every confirmed wrong answer, false match and misleading card. The evaluator gains additive keys (`forbidden`, `card`, `requires`) and a separate identification count (25 Oct, `19`). | "0 incorrect" coexisted with live wrong answers (`18` §7). | A new evaluation framework; editing existing fixtures. |
| 25 | "US" and "UK" count as names the page must use as written; an abbreviation of the candidate's own name or jurisdiction ("IDP") counts as found (25 Oct). | It removed 3 of 6 confident out-of-scope matches on both databases and newly matched "How do I get an IDP?". Answer sets were unchanged; identification sets improved (population 33→35, demo services 30→31, Tamil 30→31). | All two-letter capitals (loses "SC certificate", "IT return", "Is it OK…"); a document-type check (loses 5–16 correct matches to remove the marriage-certificate match). |
| 26 | A bare "Yes" or "No" quote counts only directly under its question; a quote cut from a Yes/No answer keeps that word (25 Oct). | The live approved answer "Apprentices can become EPF members" quoted a bare "Yes" whose question was lost; replayed over 441 verified claims, it rejected only that one. | Waiting for the migration alone. |
| 27 | A claim keeps every period (number with year, month, week or day) its quote states and adds none from outside its sentence, with units; "three days" is not "three months" (25 Oct). | 0 of 441 verified claims rejected. | Requiring the whole sentence's periods: it rejected 6 correct claims (run-on official sentences holding several cases) and caught none. |
| 28 | An amount claimed for a "test", "duplicate" or "renewal" must come from a row (or the heading directly above it) saying so (25 Oct). | The motorcycle fitness-test fee quoted the certificate-of-fitness row (W4); it rejected only that claim among 441. The nearest heading (`_section_heading`) would have let it through, because item 10's header sits above item 11. | A model check; a longer word list (paraphrases such as address/residence would be rejected). |
| 29 | A code word ("REV-101") gives no initial in `abbreviates`, so "RC" is not "REV-101 Community Certificate" (25 Oct). | A latent route for RC questions to page 17; 0 of 73/71 labelled abbreviation questions change. | Leaving it to the page-17 rename alone. |
| 30 | Operations: one log line per request (with an id) and per model call; one retry of a model call for a dropped connection, a 5xx, or (embeddings) a 400; never a timeout (25 Oct). | No logging existed; 2 of 16,859 embedding calls returned a transient 400. | An observability platform; unbounded retries. |
| 31 | Security: official-domain allow-list for ingestion (default `gov.in`, `nic.in`, `pfrda.org.in`); the connected address is checked before a page is read; 5 failed sign-ins per address per 15 minutes; byte comparison of signed tokens (25 Oct). | The README promises official pages only; these are `14` §14 items 5 and 14 and `18` RC7. | Session revocation (needs server state); a reverse-proxy rate limiter (deployment, not code). |

## Foundational decisions (context → reasoning → alternatives → consequences → status)
| Decision | Context and reasoning | Alternatives rejected | Consequences | Status |
|---|---|---|---|---|
| **Local LLM via Ollama** (`qwen3:8b`) and local embeddings (`qwen3-embedding:0.6b`) | Privacy of citizens' questions, no API costs, and a laptop demo | Cloud LLM APIs | Weaker model: inexact quotes lead to abstentions, and latency is about 5–7 s; strong code-side checks are essential | Active |
| **Human approval before persistence** | Government information must be checked by a person; LLM extraction can be wrong | Auto-saving extracted procedures | A reviewer is needed for every page and re-scrape; the provenance token ties approval to the exact text | Active, mandatory |
| **PostgreSQL + pgvector** | One database for records and vectors; transactions keep a page and its chunks consistent; cascade deletes | A separate vector database | Simple operations; similarity search is a SQL `ORDER BY` | Active |
| **Retrieval with verified citations** | The answer must be checkable by a citizen | Free-text LLM answers; summaries | Some coverage is lost to strict verification; this is accepted | Active |
| **Conservative abstention and clarification** | A wrong fee or rule is worse than "the official page does not say" | Best-guess answers | Evaluations count abstentions and clarifications separately; never as correct | Active |
| **Deterministic validation rules** for each error class found (applicant type, money, negation, back-reference, document kind) | The model's own meaning check approved wrong claims repeatedly (3/3) | Prompt-only fixes | Each rule needs positive and negative tests; rules can over-reject (see H1 in `10`) | Active |
| **Chunking on paragraph boundaries with heading-aware starts** | Facts must stay with their headings and conditions | Fixed-size token windows; repeating headings everywhere (reverted) | Simple and predictable; long tables can still split | Active |
| **No evaluation-specific code** | Scores must reflect real behaviour | Hard-coding answers or expected pages | Scores move slowly; the held-out set guards against overfitting | Active |
| **Minimal, understandable implementation** | Owner preference; a small team | Frameworks such as LangChain, or rewrites | About 5,000 lines in total | Active |
| **Official sources only** | Trust | Bank or aggregator pages that fill gaps | Gaps are documented in `06` | Active |

## Decisions of 26–27 Oct 2026 (full records)
Each record gives the context and problem, the decision, the reasoning and evidence, the alternatives rejected, and what it means now.

### 32. Re-extract removed (26 Oct; the owner's request)
- **Context:** the admin page had a Re-extract button (`POST /api/admin/re-extract`). It re-ran the model on the already-scraped, token-bound text.
- **Decision:** remove it from the route, schema, client, button and tests (`20`, Phase 3). A reviewer who wants a new draft submits the URL again.
- **Why:** fewer moving parts. Nothing else called it. The provenance token still binds approval to the scraped text.
- **Rejected:** keeping it.
- **Now:** **do not reintroduce a re-extract or re-scrape feature.** `rescrape_dry.py` in `evidence/` is a read-only audit tool, not a feature.

### 33. A human approves every ordinary procedure; the model never approves
- **Context:** the model drafts every card. Measured draft errors include:
  - page 17 named "REV-101 Community Certificate", with CAN-editing steps;
  - 38 candidate draft steps were paraphrases below 80% word overlap (`p8_candidates`);
  - N4's draft presented the head-of-family route as a universal requirement;
  - N3's draft turned form-section headings into steps;
  - N10's draft kept a 2008 submission route.
- **Decision:** only `POST /api/admin/procedures` saves, only with an admin session and a valid provenance token, and only what the reviewer left in the form.
- **Why:** a wrong fee, document or condition harms citizens. The draft cannot be trusted alone.
- **Rejected:** auto-saving drafts; a separate approval mechanism.
- **Now:** an explicit, named delegation by the owner (entry 49) lets Claude act as the human reviewer for exactly those pages, through the same workflow. It is not a new mechanism.

### 34. No page-specific rules or question-to-procedure mappings
- **Context:** many failures could be patched for one page ("marriage certificate → none", "RC → page 28").
- **Decision:** fix only general rules, using reference data (states, countries) and stored names. Measure every rule on every labelled question (`20`, the screen method).
- **Why:**
  - the app must work for official pages never seen before (`evaluate_ingestion.py`: 6 unseen URLs, 37/37);
  - hard-coding makes the evaluation dishonest and breaks with the next page.
- **Rejected:** the per-question patches above.
- **Now:** a rule that names a page, URL or question is not acceptable.

### 35. Avoid agents, layers and complexity without a demonstrated need (the owner's principle)
- **Decision:**
  - fix an existing function first;
  - no helper used once;
  - no new module, service or dependency, and no LLM layer, unless measured evidence shows the need.
- **Why:** a small team and an IT-undergraduate owner who must understand the code. Every measured "smart" addition so far (the model check, a prompt change) cost correct answers.
- **Now:** the backend is about 2,700 lines. Keep changes small, tested, and with a reason for every line.

### 36. Thresholds stay at 0.53 / 0.03 (W11, 25 Oct; re-confirmed 26–27 Oct)
- **Evidence:** scores of in-scope near misses and out-of-scope questions overlap (above). `16_W11_IDENTIFICATION_THRESHOLD_INVESTIGATION.md`.
- **Now:** the 4 colloquial RC/DL misses remain. Do not lower the threshold to fix them.

### 37. Clarification and abstention are valid outcomes
- **Why:** "the official page does not say" or "which one do you mean?" is safer than a confident wrong answer.
- **Now:**
  - the evaluator counts them separately, never as correct;
  - the citizen page shows `NO_MATCH`, `NO_ANSWER` or the server's question;
  - the owner's briefs require it.

### 38. Model check of the chosen procedure: REJECTED (26 Oct)
- **Measured:** `evidence/investigations/p4_identification/`. On 216 labelled questions, it removed all 8 confident out-of-scope matches but rejected 20 correct identifications (157 → 137). From the card alone, it scored 130.
- **Why it fails:** pages hold more than their card says ("Learner's Licence" holds the transport-vehicle age rule).
- **Now:** no LLM identification layer without strong new evidence.

### 39. Spelling out RC/DL for the search: REJECTED (27 Oct)
- **Measured:** it fixed some colloquial RC/DL misses but broke 6 other questions (IDP, VVPAT, learner's licence), as in W11.
- **Note:** the Tamil normaliser still writes DL and RC in full for Tamil input (`normalize.PROMPT`). That is separate from the English search.

### 40. Answer-prompt change for the overseas abstentions: REJECTED (27 Oct)
- **Measured:** `evidence/investigations/p6_identification/prompt_ab*`. One added sentence about the citizen's own facts fixed neither abstention (2 of 8 overseas phrasings) and changed 5 of 16 other answers.
- **Now:** the abstentions remain a known limitation.

### 41. "The whole message's page wins": REJECTED (26–27 Oct)
- **Measured:** 2–4 more correct matches, but one more false match on each database.
- **Decision instead:** phrase first, then the standalone question, then the message. When they disagree in measured ways, the citizen chooses (`03` §2.2, rule 7).

### 42. Where the citizen is decides between a service and its overseas variant (27 Oct)
- **Problem:** "I work in Dubai, can I vote?" ranked Register to Vote above the overseas page.
- **Decision:** two nearby siblings, one named for citizens abroad:
  - abroad (words, or a foreign country in any capitalisation) → the overseas page;
  - no residence clause → the other;
  - an unknown place (a city) → the scores and the choice rules.
- **Guard:** it applies only once the service itself clears the threshold. A measured regression (follow-up C4, "Can I do this at a post office?") turned a miss into a match without it.
- **Now:** in `procedure_search._decide`. Tests: `ResidenceTest` and the audience-rule API tests.

### 43. Lower-case abbreviations of stored names are read in capitals (27 Oct)
- **Decision:** "idp" → "IDP" and "eps" → "EPS", but only for a stored procedure's own abbreviation (`read_abbreviations`). A name already holding an acronym gives no initials.
- **Why:** citizens type in lower case; the abbreviation rules read capitals.
- **Rejected:** treating every short lower-case word as an abbreviation.

### 44. Unnamed documents get a question; a more specific document is not matched (27 Oct)
- **Decision:**
  - "How do I apply for a certificate in Tamil Nadu?" → "Which certificate is your question about?" (`unnamed_document`, after the search, so a real choice stays a choice);
  - a page whose headings name the asked document only with extra qualifiers ("Inter Caste Marriage Certificate" for "a marriage certificate") is not matched (`more_specific_document`).
- **Why:** both were confident false matches on stored pages.
- **Now:** a page without headings says nothing here. That was why approved page 17 still matched marriage questions.

### 45. The card rule: show a procedure the citizen did not name only with an answer from it (27 Oct)
- **Problem:** similarity-only matches showed unrelated cards (marriage certificate → page 17's card).
- **Decision:**
  - named or chosen procedures show their card at once;
  - an unnamed match shows its card only if `/api/guidance` returns verified claims; otherwise the note "No approved official information answers this question yet…";
  - follow-ups keep the open page when the other page also abstains.
- **Now:** `CitizenPage.showAndAnswer` and `answerFollowUp`, modelled by `evaluate_answers.py`.

### 46. Database outage handling: a 503 message during operation; start-up unchanged (27 Oct)
- **Problem:** a database outage during operation gave a bare 500 without a request id.
- **Decision:** one exception handler (`main.database_unavailable`) → 503 "The procedure database is unavailable. Try again."
- **Not changed:** the backend still cannot start without the database (`create_all` on import). No recovery architecture without a simple, justified fix.

### 47. Chunking (P1-3) is not combined with the migration
- **Context:** sentence-aware splitting of over-long paragraphs was prepared (`19`, P1-3). It changes the chunks of pages 15, 19 and 40, and would add page 15 to the migration.
- **Decision:** keep `rag.chunk_text` as it is for the migration. Any chunking change gets its own staging evaluation and its own approval.
- **Why:** the migration validator compares the stored chunks with `chunk_text(source_text)` and with staging. Changing both the data and the chunker at once makes failures impossible to attribute, and it re-embeds pages that would otherwise be untouched.
- **Now:** page 19's mid-sentence chunk stays. Its answer abstains safely.

### 48. Page 17 is deleted, not replaced (the owner's decision, 27 Oct)
- **Context:**
  - approved page 17 ("REV-101 Community Certificate", the e-Sevai FAQ) answers birth, death, community and income certificate questions with CAN-editing steps;
  - its income and nativity lists mix other certificates' documents;
  - a replacement with a renamed card was prepared (26 Oct) and fixed the measured answers on staging. But the page still drew certificate questions (1 misleading card measured on staging).
- **Decision:** delete it from the collection completely. No replacement, and no invented certificate procedure.
- **Rejected:** the renamed replacement (`07`, `19`: kept only as a record).
- **Now:**
  - certificate questions get no match or a clarification, until a genuine procedure exists (N8 covers births and deaths, once approved);
  - no page-specific compensation;
  - deleted on staging; production needs the owner's approval.

### 49. The delegated approval of five candidates (the owner's brief, 27 Oct)
- **Decision:** Claude may verify, correct, test and approve N1, N3, N4, N8 and N10 through the existing admin workflow, including into the approved database, without asking per candidate. It must apply the 12 quality rules (brief §5.4).
- **Limits:** no other page; no destructive production operation; not the migration. N2, N5, N6, N7, N9 and N11 are deferred by the owner.
- **Now:** N1, N3, N4 and N8 are reviewed, not approved. N10 is deferred (entry 50).

### 50. N10 (new ration card, consumer.tn.gov.in) deferred (27 Oct)
- **Evidence:** the page's own text promises online applications "by September 2008", SMS status "by end 2008", a Rs 5 fee and RPAD postal submission. Official search results point to the TNPDS portal and e-Sevai PDS-501 for current applications, but no readable official page could be fetched.
- **Decision:** do not approve outdated submission instructions.
- **Now:** revisit with a current official page; it needs the owner, because the source URL changes.

### 51. Evaluation labels must name exactly one page (27 Oct)
- **Problem:** fixtures match pages by URL substring. `https://www.passportindia.gov.in/psp/Apply` (passport) is a prefix of `…/psp/ApplyPCC` (N3), and "uidai" matches both Aadhaar update and N4. A passport question answered by the PCC page would have been scored correct.
- **Decision:**
  - the evaluators match a fragment only when no letter or digit follows it;
  - the fixtures were relabelled to the same pages they always meant: `psp/Apply`, `updating-data-on-aadhaar`.
- **Checked:** no other fragment's matches changed. Not yet exercised by a run.

### 52. Collection changes are labelled with `requires` / `unless`, before running (27 Oct; planned)
- **Context:** the fixtures describe the stored collection. When the owner deletes page 17 or approves candidates, some expectations become false.
- **Decision:**
  - a case about a page that may be absent carries `requires`;
  - a case about its absence carries `unless`;
  - new expectations are written from the stored pages before any run, and each change is recorded with its reason.
- **Never:** to raise a score.
- **Now:** `10`, P1.1–P1.2.

### 53. Admin routes run in-process for delegated and rehearsal work (27 Oct)
- **Context:** the admin password is not available to Claude and must not be read from `.env`.
- **Decision:** `evidence/investigations/p9_final/admin_workflow.py` runs the application's own routes with `TestClient`, replacing only `require_admin`. Extraction, the provenance token, chunking, embedding and saving are the application's code.
- **Guards:** it refuses deletes in `procedureassist`, and approvals there except the five delegated URLs.
- **Rejected:**
  - direct SQL writes (they bypass the workflow);
  - minting a session cookie from `SECRET_KEY` (it would read secrets);
  - asking the owner to sign in for each page (the delegation says not to ask).
- **Now:** use it only for delegated approvals and staging/scratch rehearsals. Human migration steps still go through the admin page.

### 54. A scratch copy of the approved database for production-like tests (27 Oct)
- **Decision:** test the page 17 deletion (rolled back) and the candidates on `procedureassist_scratch`, a restore of a fresh dump of approved, before touching staging or production.
- **Why:** the behaviour depends on the whole collection; the test database is empty.
- **Now:** it exists (24 / 122, equal to approved). It is not one of the two project databases; drop it when no longer needed and record that.

### 55. Delete or approve only through the workflow, with a backup first (27 Oct, re-applied)
- **Done:** staging was dumped before its page 17 deletion, and approved was dumped before any candidate work.
- **Now:** keep that order: dump, verify, then write.

### 56. One-letter pieces of a procedure name are not words of it (28 Oct; code)
- **Problem:** found by testing N1 on a production copy. `acronym_names("PAN", "Instant e-PAN", question)` accepts "another word of the name" from the question. The one-letter piece "e" of "e-PAN" matched any "e-…" word, so "How do I register on the income tax e-filing portal with my PAN?" went to Instant e-PAN with a card. The correct page, "Register on the e-Filing Portal", scored 0.774 vs 0.687.
- **Decision:** one line in `acronym_names`: name pieces shorter than two characters are ignored. A unit test asserts it, and it failed before the fix.
- **Evidence:** on the production copy with the candidates, 1 of 300 labelled cases changed (that one, now correct); 252 backend tests OK.
- **Rejected:** a page-specific exception for "e-PAN".
- **Now:** kept although N1 is deferred. It protects any future "e-…" or "ITR-n" style name.

### 57. N1 Instant e-PAN deferred, not approved (28 Oct)
- **Evidence:** on the production copy, a lost or duplicate PAN question becomes a choice that includes Instant e-PAN. Choosing it gives the verified answer "To get a duplicate PAN card, you can apply for an Instant e-PAN…", which the page itself contradicts: an existing PAN holder is not eligible.
- **Why defer:** the owner's approval rules require every important claim to be supported. The cause is general (the close-call rule and the meaning check), so no card correction prevents it.
- **Rejected:** approving N1 and accepting the path; a page-specific block of "duplicate" questions.
- **Now:** to approve N1 later, first make a general change with its own measurement. Either the close-call rule stops offering pages the name filter rejected, or duplicate/renewal/test claims must come from a passage saying so. See `p9_final/candidate_review_27oct.md`.

### 58. N3, N4 and N8 approved with measured, citizen-safe side effects (28 Oct)
- **N8:** fixes the live misleading birth and death certificate answers. The cost is 7 false identifications of Tamil Nadu certificate questions, all abstaining with no card (the card rule, entry 45; the document-kind rule).
- **N3:** the cost is passport-fee choices, where both options abstain, and lower-case "idp" losing its match because the abbreviation rule looks only at the top 3 pages.
- **N4:** no side effect found.
- **Rejected:**
  - holding N8 until a document-type identification check exists (entry 25 measured such a check costing 5–16 correct matches);
  - widening the abbreviation window to more than 3 pages now. That changes the abbreviation override for every question, and it needs the full screen first.
- **Now:** the false identifications are reported as such in the evaluations; nothing counts them as correct.
