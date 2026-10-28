# 20 — Reliability, generalisation and simplification (26 Oct 2026)

**Status:** code phases complete and measured. **Database phase not started:** it needs the owner's decisions (see "Phase 5"). Brief: "Complete Reliability, Generalisation & Simplification".

**27 Oct 2026, a further brief:** "Resolve Remaining Identification Failures". Code and evaluation done and measured; no database written; stopped before any migration or approval. See "Remaining identification failures" below.

**Ground rules kept:**
- No database written: the approved and staging checksums are recorded in each run.
- `.env` untouched; nothing committed.
- Procedure content enters the database only through human review and explicit approval. Claude cannot be that reviewer, so every database write waits for Arun's decision (see "Data plan").

## Phase 1 — Reconnaissance (done)
- **Code:** unchanged since the final measured snapshot (`19`, `evidence/evaluations/master_final/`). Baselines:
  - staging main 75/80, held-out 23/27;
  - approved main 74/80, held-out 24/27;
  - identification sets 11/14, 35/42, 31/37, 31/36;
  - safety set: staging 43/59, approved 38/53.
- **Databases:** approved 24 pages / 122 chunks (`016980ee…` / `3e45c78f…`); staging 26 / 140 (`8aba737f…` / `93000b69…`).
- **"Re-scrape":** the application had no action that re-scrapes a saved procedure; the saved list offers only delete. The one re-processing feature was **Re-extract**: during review it re-ran the model on the already-scraped, token-bound text. That is the feature removed in Phase 3.

## Phase 2 — Data plan (prepared; NOT executed)
**Reconciled against the current databases (26 Oct; read-only).**
- **Approved:** 24 pages / 122 chunks; **staging:** 26 / 140; checksums unchanged.
- The plan in `19` ("Final migration approval checklist") matches the actual records exactly:
  - **9 replacements:** 17, 18, 19, 20, 27, 35, 36, 37, 38 (their chunks are listed in `07`);
  - **4 URL moves:** 16, 31, 32, 33;
  - **2 additions:** 39, 40;
  - **11 untouched:** 15, 21, 22, 23, 24, 25, 26, 28, 29, 30, 34.
- **Foreign keys:** deleting a procedure cascades to its chunks, so no orphans.
- **Duplicates:** `source_url` is unique, so a replacement must delete before it approves, and a move must approve the new URL before deleting the old.
- `validate_migration.py` verifies counts, text, chunks, vectors, FAQ pairs and every card field.

**New procedure collection: candidates found and tested through the app's own scraper** (`evidence/investigations/p2_collection/`). Only official domains were considered (the allow-list); aggregator sites (bankbazaar, kanakkupillai, cleartax, housing.com …) were excluded even where they ranked first.

| # | Candidate | Official URL | Jurisdiction | Ingestible? |
|---|---|---|---|---|
| N1 | Instant e-PAN | `https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/instant-e-pan?mobile-app=1` | India | Yes (8,245 chars) |
| N2 | e-Verify an income tax return | `https://www.incometax.gov.in/iec/foportal/help/how-to-e-verify-your-e-filing-return?mobile-app=1` | India | Yes (12,285) |
| N3 | Police Clearance Certificate | `https://www.passportindia.gov.in/psp/ApplyPCC` | India | Yes (3,336) |
| N4 | Aadhaar enrolment | `https://uidai.gov.in/en/aadhaar-enrolment` | India | Yes (3,747); overlaps stored page 35 (enrolment at post offices) |
| N5 | PM Jeevan Jyoti Bima Yojana | `https://www.indiapost.gov.in/insurance-services/pmjjby` | India | Yes (1,725) |
| N6 | PM Suraksha Bima Yojana | `https://www.indiapost.gov.in/insurance-services/pmsby` | India | Yes (1,661) |
| N7 | National Pension System (All Citizen) | `https://pfrda.org.in/web/pfrda/schemes/national-pension-system/nps-for-all-citizen-models` | India | Yes (11,116) |
| N8 | Birth and death registration (TN rules; Krishnagiri district page) | `https://krishnagiri.nic.in/scheme/civil-registration-system/` | Tamil Nadu | Yes (1,684) |
| N9 | Revenue social security pensions (old age, widow, …; Chennai district table) | `https://chennai.nic.in/oap-eligibility/` | Tamil Nadu | Yes (3,319) |
| N10 | New ration (family) card | `https://consumer.tn.gov.in/eligibility_ration.htm` | Tamil Nadu | Yes, through the new browser fallback (10,548) |
| N11 | Social security schemes for differently abled persons | `https://www.scd.tn.gov.in/social_sec_schemes.php` | Tamil Nadu | Yes, through the new browser fallback (5,973) |

**Rejected, with the reason:**

| Candidate | Reason |
|---|---|
| Legal heir certificate | No dedicated official HTML page. District pages list it among many certificates (Perambalur, Chennai, Tiruchirappalli), duplicating and partly contradicting page 17's lists. |
| Marriage registration (TN) | Only press releases (PDF) and portal pages |
| Patta / chitta, encumbrance certificate | District pages are link lists; the portals are applications |
| Employment exchange registration | District page too thin (688 chars); the FAQ is a PDF |
| Kalaignar Magalir Urimai Thogai | Official site does not load, even in a browser |
| PM-KISAN | Unreachable |
| PM-JAY (nha.gov.in) | JavaScript app with no usable text |
| EPFO FAQ | 404 |
| ECI resident-electors FAQ | Redirects to a 404 page served as success; the scraper now rejects such pages |
| e-Aadhaar download FAQ | 404 |
| India Post savings app | 503 |
| ECI help FAQ (45,171 chars) | Usable, but a broad voting FAQ overlapping pages 19–21 |
| TN Revenue Administration scheme page | 404 |

**With the 11, the collection would hold 37 procedures** (26 after the migration, plus 11). Each candidate's draft card, text, chunks and quality flags are prepared as a review packet (`p2_collection/review_packets.*`). They are for a human reviewer; nothing is saved.

**The review packets** (all 11 went through the unmodified scrape → extract path):
- The model's drafts need the reviewer. Three put an eligibility phrase or a bank in the jurisdiction field, and two named a multi-scheme page after one scheme. This is why approval must stay human.
- The notes below are suggestions from each page's own text. The reviewer decides.
- Department and jurisdiction follow the stored cards' convention ("India Post" / "India", "Passport Seva" / "India").

| # | Draft (model) | Reviewer notes |
|---|---|---|
| N1 | Instant e-PAN; Income Tax Department; India | Card usable. The source has a YouTube link paragraph (harmless). |
| N2 | "e-Verify"; Income Tax Department; India | Name: "e-Verify an Income Tax Return". Shares 9 boilerplate paragraphs with the e-Filing registration page; identification may offer both. |
| N3 | Apply for Police Clearance Certificate; Passport Seva; *none* | Jurisdiction: India. Shares 12 template paragraphs with the passport page (15); identification may offer both for vague passport questions. |
| N4 | Aadhaar Enrolment; UIDAI; India | Overlaps page 35 (enrolment at post offices) and shares 7 paragraphs with page 18. **The owner decides whether to include it.** |
| N5 | PMJJBY; "Life Insurance Corporation of India"; "All savings bank account holders …" | Department: India Post; jurisdiction: India. The step "The scheme is administered by LIC" is not a step. |
| N6 | PMSBY; "Public Sector General Insurance Companies …"; "Participating banks" | Department: India Post; jurisdiction: India. The last step is not a step. |
| N7 | National Pension System (NPS) Individual Pension Account; PFRDA; India | Card usable. |
| N8 | Registration of Births and Deaths; "Civil Registration System"; Tamil Nadu | Eligibility: empty ("All citizens" is not stated on the page). The page is a district (Krishnagiri) page describing the state rules. |
| N9 | "Old Age Pension"; "IGNOAPS"; "District" | The page is a table of several revenue pensions. Name it for the table; jurisdiction: Tamil Nadu; department: Revenue Department. The steps are eligibility checks, and the page names only the e-District CSC service. |
| N10 | Application for a new ration card; Civil Supplies and Consumer Protection Department; Tamil Nadu | Card usable. The page is dated (it refers to the 2008 online launch); the reviewer confirms it is current. |
| N11 | "Unemployment Allowance for the Differently Abled Persons"; …; Tamil Nadu | The page lists several schemes. Name: "Social security schemes for differently abled persons"; the summary covers them all. |

## Phase 3 — Re-extract removed (done)
| Where | Removed |
|---|---|
| `backend/routes.py` | `POST /api/admin/re-extract` (`re_extract_procedure`), and the now-unused `ReExtractRequest` and `ProcedureDraft` imports |
| `backend/schemas.py` | `ReExtractRequest` |
| `frontend/src/api.ts` | `reExtractProcedure`, `ReExtractRequest`, and the now-unused `ScrapeResult` type |
| `frontend/src/AdminPage.tsx` | the Re-extract button and `handleReExtract` |
| `tests/test_routes.py` | 4 re-extract tests and their fixture |
| `frontend/src/AdminPage.test.tsx` | the re-extract test |
| `tests/test_auth.py` | the admin-route floor 6 → 5, so every remaining admin route is still checked for a session |
| Docs `01`, `02`, `03` | Mentions of Re-extract updated |

**Kept:**
- URL submission → scrape → extract → review → approve → index;
- the provenance token, which still binds approval to the scraped text;
- Discard.

To get a new draft, the reviewer submits the URL again. No scheduled job, database field or other caller existed.

**Not edited:** `13` and `14` belong to the other session and still describe the removed route. `rescrape_dry.py` (evidence) is a read-only audit tool, not an application feature; the migration checklist uses it.

**Search after removal:** no code reference to re-extract remains in `backend/`, `frontend/src/`, `scripts/` or `tests/`.

## Phase 4 — Identification and ingestion robustness (in progress)
**Measured and rejected: a model check of the chosen procedure.**
- **What was tried:** the existing qwen3:8b asked "is this page right for the question?" (`evidence/investigations/p4_identification/`).
- **Staging, 216 distinct labelled questions:**
  - from the card plus the best passage, it removed all 8 confident out-of-scope matches (PAN correction, new PAN, PAN name change, marriage certificate ×2, lower-case UK licence, Kerala community certificate, vague certificate question);
  - but it also rejected **20 correct identifications** (157 → 137);
  - from the card alone it was worse (130).
- **Why:** pages hold more than their card says. "Learner's Licence" holds the transport-vehicle age rule, and "How to Vote" holds the helpline number.
- **Score gating does not help:** false matches score 0.524–0.657, and wrongly rejected correct matches 0.475–0.811.

**Added: jurisdiction from metadata** (`procedure_search.covers`).
- A procedure whose jurisdiction names an Indian state is not matched to a question that names only other states or territories, in any capitalisation.
- Central procedures, whatever their jurisdiction text, cover all states.
- It uses a fixed list of India's states and union territories (reference data, not page-specific). Tests: `CoversTest`.

**Ingestion robustness** (found by test-scraping unseen official URLs):
- **Browser fallback on a failed connection.** Some Tamil Nadu servers send an incomplete TLS certificate chain. The HTTP client rejects them; a browser completes and verifies the chain. `scrape_url` now uses the existing browser fallback when the direct fetch cannot connect.
  - Client errors (4xx, PDFs, private addresses) still never fall back.
  - Certificate verification is not weakened.
  - Pages that fetch today are unaffected, so the migration's verified texts are unchanged.
- **Error pages served as success.** A short page saying "404" or "not found" (ECI served one with status 200) is no longer accepted as content.
  - No stored page in either database is affected.

**New regression probes:** `fixtures/evaluation/generalisation.json` (17 cases): lower-case and other-state jurisdictions, related documents and actions no page covers, a vague question, and in-scope contrasts.

## Phase 6 — Verification (done on the current databases)
**Suite:** `evidence/evaluations/gen_final/`, from a frozen snapshot. Both databases' checksums are identical before and after.

| Evaluation | Before this brief | Now |
|---|---|---|
| Staging main / held-out | 75/80, 23/27 | 75/80, 23/27: **0 of 107 cases changed** (claims included) |
| Approved main / held-out | 74/80, 24/27 | 74/80, 24/27: **0 of 107 changed** |
| Identification sets (staging) | 11/14, 35/42, 31/37, 31/36 | Identical |
| Follow-ups (17), audit probe (42) | 17/17; — | Identical |
| Safety set: staging / approved | 43/59, 38/53 | Identical (0 of 59 changed on each) |
| **New probes** (`generalisation.json`): staging / approved | — (not run on the earlier code) | **13/17 / 13/17** |
| **Ingestion acceptance** (`scripts/evaluate_ingestion.py`; 3 unseen official URLs, test database, rolled back) | — | **22/22 checks** |

**Ingestion acceptance in detail.** PMSBY, Police Clearance Certificate and TN birth registration, all absent from both databases, each went through:
1. submit;
2. scrape and extract;
3. approve and save;
4. chunk and index, with 1,024-value embeddings;
5. identify: the right page was matched;
6. guidance: quotes from that page only.

A question the page does not answer (the PMSBY premium, which is only in linked PDFs) gets no answer. Two unrelated questions get no match. Nothing was kept.

**A correction made during the run:** the first version of the test expected the PMSBY premium. The page does not state it, so the system's abstention was right and the expectation was wrong. The case was changed to a fact the page states (ages 18 to 70), and the premium became a must-abstain check.

**False positives and false negatives (identification, measured; the same on staging and approved):**

| Kind | Cases |
|---|---|
| **Confident wrong page, out of scope (false positives)** | Safety set: marriage certificate ×2, PAN name change. New probes: PAN correction, new PAN, lower-case "uk" licence. Answers abstain on the stored data, but the card is shown. |
| **Vague question matched instead of asked** | "How do I apply for a certificate in Tamil Nadu?" → page 17 |
| **Confident wrong page, in scope** | "I work in Dubai. Can I vote in India?" → Register to Vote instead of Overseas voters; the held-out grace-period fee → the renewal page (tie rule) |
| **Misses, in scope (false negatives)** | The 4 W11 colloquial or abbreviated questions (the threshold stays 0.53) |
| **Fixed in this brief** | "community certificate in kerala" (other state, lower case) |

The system does not abstain on everything: the main sets answer 75/80 (staging) and 74/80 (approved), and all 7 in-scope probe contrasts are matched correctly.

**Tests:**
- backend **235** OK (re-extract tests removed, new tests for the state rule, browser fallback and error pages);
- frontend **64** passed;
- type check and unused-code check OK;
- production build OK.

**Not run:**
- live outage drills;
- real-speech tests;
- concurrent load;
- a manual browser session. The UI was not exercised by hand in this pass; its tests and build pass.

## Remaining identification failures (27 Oct 2026)
**Ground rules kept:** no database written (both checksums are identical before and after every run); `.env` untouched; nothing committed; no threshold change; no new model check, service, module or dependency; no rule names a page, a procedure or a question.

### How each failure was investigated
- **Trace of the real route** (`evidence/investigations/p5_failures/trace.py`, outputs `trace_*.txt`). The application code runs unchanged. Wrappers record:
  - every text `_decide` is given;
  - its top three pages and scores;
  - classify, the abbreviation override, and the name and state checks for each candidate;
  - the final status and `named`.
- **Screen of candidate rules** (`screen.py`, run with `REAL=ALLask+F8p`):
  - **final outputs** are `screen_final_*.txt`, which list every question the adopted rules still get wrong;
  - `screen_procedureassist*.txt`, `screen_f8_*.txt` and `residual_*.txt` are the earlier steps, from before the acronym-home rule;
  - every labelled English question, 288 distinct on staging and 286 on approved, from all existing sets plus the safety, generalisation and new sets;
  - each candidate rule is a flag on a copy of the route;
  - the copy with the adopted flags is asserted equal to the live route on every question;
  - need extraction and query embeddings are cached, so every variant sees the same model output.
- **Answers for the remaining false matches** (`false_match_answers.py`): the real guidance for each question still matched to an unrelated page.
- **New regression set** `fixtures/evaluation/identification_failures.json` (74 cases), written from the stored pages before any fix. It holds:
  - variants of every listed failure;
  - the categories asked for: Indian states, foreign jurisdictions, similar documents, different actions on one document, unnamed certificates, overseas citizens, abbreviations and lower case, colloquial wording, out of scope.

  Seven cases that repeated existing questions were replaced by fresh variants. One of them conflicted with held-out "How do I apply for a licence?", which expects a choice; that expectation stands. Existing fixtures are unchanged.

### Root cause and fix, per failure
| Failure (traced) | Root cause | Fix |
|---|---|---|
| **Marriage certificate ×2** → page 17 at 0.60–0.66. No check applies: no state, no capitalised name. | **Retrieval and misleading metadata.** Page 17's lists of required documents look like the question: "Marriage Registration Certificate" is a required document, and "Inter Caste Marriage Certificate" is another certificate. The stored name is a button label. Approved page 17 has no FAQ headings, so neither a name nor a heading tells its ten certificates apart. | **Not fixed at identification.** Document checks lost 5–16 correct matches (P0-2). The answer abstains on both databases (checked), and the citizen page now shows no card for it (§4): the citizen sees "We don't have an approved procedure…". |
| **PAN name change, correction, new PAN.** The override sends them to Link PAN with Aadhaar, with `named` true. Without it, the e-Filing login page wins by similarity. | **Identification ignored the action.** "PAN", written inside "Link PAN with Aadhaar", counted as that procedure's own abbreviation. The e-Filing page only uses the PAN as a login field. For "new PAN card" its answer gave the e-Filing registration steps: verified quotes, for a different question (checked, both databases). | (a) **A term written inside a longer name names it only when the question also uses another word of the name** (`acronym_names`): "linking PAN with Aadhaar" still does; initials ("DL") and a bracketed short form ("(EPS)") are unchanged. (b) **When the question uses an acronym written in a stored procedure's name, a page is about it only if one of the question's acronyms or its words name that page.** "Register on the e-filing portal with my PAN" still matches the e-Filing page. (c) A need phrase is checked with its standalone question: "get a duplicate" alone dropped the PAN card. |
| **Lower-case "uk"** → page 24 at 0.639 | **Jurisdiction detection:** country codes were matched as written (lower-case "us" is a word) | "uk" counts in any case |
| **"How do I apply for a certificate in Tamil Nadu?"** → page 17 at 0.59–0.61 | **Query understanding:** "certificate", "tamil" and "nadu" counted as naming a service | **A document noun with no kind and nothing else specific** gets "Which certificate is your question about? Please say its name or what it is for." States and general words ("from", "online", "government") do not count. A kind does ("registration certificate"). The check runs after the search, so a choice the search offers stays a choice. |
| **"I work in Dubai. Can I vote in India?"** The phrase "vote in India" goes to Register to Vote (0.676). The standalone question and the whole message ranked Overseas first, but the name check rejected them. | **Query understanding and jurisdiction.** The extraction dropped the decisive detail. Where the citizen works was treated as a name the page must contain, so the choice rule never ran. The same cause appeared elsewhere: a state ("register to vote in Kerala") blocked central pages, and "I am an NRI" lost the detail in both the phrase and its question. | **India, its states and where the citizen lives, works, studies or travels** (after "live in", "work in", "travelling to"…) are not names a page must use; `covers` still checks states. **The citizen also chooses when the whole message alone confidently matches another page.** Dubai now gets a choice: Register to Vote or Overseas (NRI) Voter Registration. |
| **Four colloquial or abbreviated misses**: right page ranked first at 0.445–0.529 | **Confidence threshold and retrieval:** colloquial wording and RC/DL score low | **Not fixed; they abstain.** The threshold stays. Offering the best near miss as a choice (screened again) helped 1 question and offered unrelated pages for 2 out-of-scope ones. Spelling out RC/DL misroutes (W11). |

**Clarification and abstention (§3), as implemented:**
- A question naming no particular document is asked which one.
- When several procedures are plausible, the citizen chooses. This now also applies when the phrase and a confident whole message disagree.
- A question clearly outside the stored procedures gets no match.

**Citizen page (§4):**
- **Named or chosen:** a procedure the citizen named or chose is shown at once, as before, even when its page cannot answer.
- **Found only by similar words:** shown only with an answer from its page. When that page answers nothing, no card is shown and nothing is left open. The citizen sees "We don't have an approved procedure that matches this yet…", and the next question is searched afresh.
- **Follow-ups:** a page the search finds replaces the open one only when it answers. Otherwise the open procedure and its own reply stay.
- **Not changed:** multi-need sections still show a matched procedure's name above a refusal.

`scripts/evaluate_answers.py` and the follow-up scenarios (`evaluations/rag_fixes/followup_scenarios.py`, dated note) model the same rules. The audit probe (`rag_audit/scripts/probe.py`) still replays its older follow-up routing, unchanged, and is compared run to run only.

### Results (`evidence/evaluations/p5_after/`, frozen snapshot; before: `gen_final`, same backend as before this brief; new set before: `p5_before`)
| Evaluation | Before | After |
|---|---|---|
| Staging main / held-out | 75/80, 23/27 | Same: **0 of 107 cases changed** (claims included) |
| Approved main / held-out | 74/80, 24/27 | Same: **0 of 107 changed** |
| Identification sets (staging): multi-need, population, demo, Tamil | 11/14, 35/42, 31/37, 31/36 | 11/14, **36/42, 32/37**, 31/36. The PAN name change is fixed in two; "I turned 18…" moves from the wrong page to a choice in two. |
| Follow-ups (17) | 17/17 | 17/17. "What about the certificate?" on the RC page no longer matches page 17; same answer. |
| Audit probe (42) | — | Only Dubai changed: wrong page → choice |
| Safety set: staging / approved | 43/59, 38/53 | **44/59, 39/53.** PAN name change fixed; Dubai → choice. On staging, the imported-car follow-up turns from a routing failure into a missed answer on the right page. |
| Generalisation set: staging / approved | 13/17, 13/17 | **17/17, 17/17** |
| **New set** (74): staging / approved | 48/74, 41/74 | **61/74, 54/74**: 13 fixed on each; 2–3 more moved from a wrong page to a choice; none worse |
| Ingestion acceptance | 22/22 | **22/22.** A first run failed one live extraction: the Police Clearance page did not render in time, with the scraper unchanged. Both runs are kept. |

**Identification over every labelled English question** (the screen; identification only):

| | Staging, before → after | Approved, before → after |
|---|---|---|
| Correct matches (in scope: 218 / 216) | 185 → **188** | 178 → **181** |
| Wrong page, in scope | 15 → **9** | 17 → **12** |
| Asked to choose (in scope) | 10 → 15 | 10 → 14 |
| False negatives (missed, in scope) | 8 → **6** | 11 → **9** |
| Correct abstentions (out of scope: 59) | 44 → **53** | 43 → **52** |
| **False positives** (out of scope, matched) | 10 → **4** | 11 → **4** |
| Correct clarifications (no document named: 6) | 0 → **6** | 0 → **6** |
| Regressions (a question that got worse) | **0** | **0** |

The extra choices in scope are clarifications between two plausible pages, each including the right one: Dubai, Canada, NRI and "I turned 18" ×2 on staging. The fixtures count them as failures.

**Tests:**
- backend **244** OK (235 → 244);
- frontend **67** passed (64 → 67);
- type check with unused-code flags, and the production build, OK.

The new frontend tests fail on the old behaviour (checked) and pass on the new. Existing unit tests that open a procedure card were given `named: true`, which is their real precondition; what they verify is unchanged. One unit test was replaced. It asserted that a UK page fails the name check for a question naming India. India is now the jurisdiction every stored page covers (official Indian domains only), so the test now checks that India and its states are not names to find, and that another country still is.

### Measured and rejected
- **The whole message's page wins** (instead of a choice): 2–4 more correct matches, but one more false match on each database, against the accepted phrase-first design.
- **A near miss offered as a choice:** see the four misses above.
- **Document-kind checks against page text** (P0-2, again).

The threshold was not lowered, and no model check was added.

### Remaining limitations (not claimed fixed)
- **Overseas wording the ranking does not separate:** Saudi Arabia, Singapore and lower-case "i work in dubai" still go to Register to Vote. "I live abroad", Canada, NRI and Dubai ask the citizen to choose.
- **Changing an address in the electoral roll goes to the Overseas page**, which also states Form 8 (ranking).
- **Marriage certificate (×3)** is still matched to page 17 at identification. The answer abstains and no card is shown.
- **"What is the fee to apply for a PAN card?"** still matches Link PAN with Aadhaar on staging (that page states the linking fee); its answer abstains. On approved it is a choice.
- **Approved data only (page 17 without headings):** "birth certificate in Tamil Nadu" is matched, and its answer gives the CAN-editing steps. That is a misleading answer; staging page 17 abstains. The planned deletion of page 17 (owner decision of 27 Oct; `19`) removes it; not executed. On approved, inter caste, widow, OBC and solvency certificates are also missed.
- **Lower-case abbreviations are not abbreviations:** "how do i get an idp" gets no match on staging and the Aadhaar page on approved.
- **Still failing as before:** the four colloquial misses and the held-out grace-period fee.
- **`named` for a term written inside a name now needs another word of that name.** "What about ITR-1?" asked on another page is answered there first; no change in the 17 follow-up scenarios.
- **Background that confidently matches another page now gives a choice**, with the requested page first, instead of being ignored. This is seen in a mocked unit test only; no labelled question changed.

### Changed files (this brief)
| File | Change |
|---|---|
| `backend/procedure_search.py` (+81 / −17) | Lower-case "uk"; jurisdiction and citizen's place in the name check; `acronym_names`; acronym-home check; whole-message choice rule; `unnamed_document` |
| `backend/routes.py` (+6 / −1) | The which-document question, after the search |
| `frontend/src/CitizenPage.tsx` | Card only for a named or chosen procedure, or with an answer; follow-ups keep the open page when neither answers |
| `tests/test_identify.py`, `frontend/src/CitizenPage.test.tsx` | +9 backend and +3 frontend tests; preconditions as above |
| `scripts/evaluate_answers.py` (+8 / −3), `evidence/evaluations/rag_fixes/followup_scenarios.py` | Model the new card and follow-up rules |
| `fixtures/evaluation/identification_failures.json` (new) | 74 regression cases |
| `README.md`, handoff `00`, `03`, `10`, `20` | Documentation |

## Phase 5 — Database replacement and new collection (NOT started; needs the owner)
**Not done, on purpose.**
- Every write is procedure content, and the project's rule, repeated in this brief, is that content enters only through **human** review and explicit approval in the admin page.
- Claude cannot be that reviewer.
- The migration checklist (`19`, "Final migration approval checklist") still has open owner decisions: plan approval, card values, reviewer confirmation, maintenance window and traffic pause.

**Ready for the owner:**
1. **The nine replacements, four moves and two additions:** the exact plan, card values, reviewer table, sequence, backup and failure procedure are in `19`. The validator and its self-test are in `07` / `19`.
2. **The new collection:** 11 verified candidates (N1–N11 above) with review packets and reviewer notes. They are approved through the same admin page after the migration. The owner decides which to include (N4 overlaps page 35).

## Changed files (this brief)
| File | Change |
|---|---|
| `backend/routes.py`, `backend/schemas.py` | Re-extract route and schema removed |
| `frontend/src/api.ts`, `AdminPage.tsx` (+ tests) | Re-extract client, button and handler removed; unused `ScrapeResult` type removed |
| `backend/procedure_search.py` | `covers`: state jurisdiction from metadata |
| `backend/scraper.py` | Browser fallback when the direct fetch cannot connect; short error pages rejected |
| `tests/test_routes.py`, `test_auth.py`, `test_identify.py`, `test_scraper.py` | Re-extract tests removed; route floor 5; tests for the new rules |
| `fixtures/evaluation/generalisation.json` (new) | 17 general identification probes |
| `scripts/evaluate_ingestion.py` (new) | End-to-end ingestion acceptance on unseen URLs (test database, rolled back) |
| `README.md`, handoff `01`, `02`, `03`, `20` | Documentation |

**Size:** tracked files +68 / −167 for this brief (the removal outweighs the additions); new files: the fixture and the acceptance script (~150 lines). No new dependency, module or service.
