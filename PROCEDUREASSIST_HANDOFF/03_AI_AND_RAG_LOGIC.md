# 03 — AI and RAG logic

Three rules shape everything here:
- The model proposes and code decides. Every answer claim must carry a word-for-word quote from a retrieved official passage, and deterministic code checks it.
- When in doubt, abstain or ask. Never fill a gap from general knowledge.
- Prompts are kept short and general. Rules that must always hold are written in code with tests, not in prompts.

## 1. Ingestion: scraping → text → chunks → embeddings

### Scraping (`backend/scraper.py`)
- **URL safety.** `validate_url` allows only http/https URLs that resolve to public addresses. It re-checks every redirect, and Playwright blocks private-address sub-requests. Since 25 Oct (`19`), the address actually connected to is also checked before a page is read, which closes DNS rebinding for the page itself. It is not closed for a rendered page's scripts and styles.
- **Official domains only (25 Oct).** `require_official`: the submitted URL and the final URL after redirects must be on `OFFICIAL_SOURCE_DOMAINS` (default `gov.in`, `nic.in`, `pfrda.org.in`) or a subdomain.
- **Fetching.** A static fetch comes first. Playwright Chromium is used only when the static text is too short or is a "loading / enable JavaScript" placeholder.

**`clean_html` turns the page into paragraphs (blocks separated by a blank line):**
- **Removed:**
  - script, style, nav, header and footer elements, plus `aside`;
  - anything with role navigation, banner or contentinfo, and breadcrumbs;
  - hidden elements (`hidden`, `aria-hidden`, `display:none`).
- **Main content:** if the page has `<main>`, only that is used.
- **A block is (fixed 23 Oct 2026):**
  - a content tag: h1–h6, p, li, th, td, dt, dd, label, legend, **summary** (accordion questions);
  - **a table row** without nested lists, headings or tables, kept as one paragraph so a fee stays with its purpose ("8 Renewal of driving licence Rs. 200.00/-");
  - **a `<div>` or `<span>` that holds text itself** rather than other blocks (EPFO scheme cards, Tamil Nadu e-Sevai accordion questions, UIDAI labels, India Post's "*Inclusive of GST").
- **Fee sub-rows** (`_row_context`). A table row whose first cell is empty continues the numbered row above it. The scraper prefixes that row's text, so "(b) Motor cycle Rupees Three Hundred Only" is stored as "4. Issue or renewal of certificate of registration …: (b) Motor cycle Rupees Three Hundred Only". A "(c) …:" label row also heads its "i)", "ii)" rows, but never a sibling "(d)" row.
- **Dropped blocks:**
  - a block identical to the previous one;
  - a block where `is_menu` fires: the same four words three or more times and no sentence end (the income-tax site menus).

### Approval
The admin reviews the draft and the text. Approval stores `source_text` exactly as scraped, together with the reviewed name and summary.

### Chunking (`rag.chunk_text`)
- Chunks are about 1,000 characters, cut on paragraph boundaries; a paragraph longer than that is split at a space.
- **Heading-aware start (fixed 23 Oct 2026).** When a chunk fills up, the next one starts at the last heading of the full one, if that heading's section so far is at most 500 characters. A heading is a line of at most 120 characters ending in "?" or ":", e.g. "How do I vote in person?" or "9. What are the documents required for applying for Income Certificate?".
  - This keeps a list with its heading and first items.
  - Otherwise the old rule applies: a short (≤ 200 character) last paragraph is repeated.
- **Rejected:** repeating a section heading on every later chunk. It attached stale headings to unrelated sections (see `11_DECISION_LOG.md`).

### Embeddings
`qwen3-embedding:0.6b` with 1024 dimensions. Queries get an instruction prefix and documents don't. Vectors are stored in `procedure_chunks.embedding`, and the cosine distance is computed by pgvector.

## 2. Answering a citizen

### 2.1 Normalisation (`backend/normalize.py`)
- **English** questions are used as they are.
- **Tamil, Romanized Tamil and mixed** questions are rewritten by `qwen3:8b` into one English search query, or flagged as needing clarification.
- The citizen sees the "Searched as" query. Answers stay in English.

### 2.2 Identification (`backend/procedure_search.py`)
1. **No service named.** A question made only of generic words ("How do I renew?") gets a clarification request instead of a search.
   - **Since 27 Oct (`20`):** a question about a certificate, licence, permit or card that does not say which one, and names nothing else ("How do I apply for a certificate in Tamil Nadu?"), is asked "Which certificate…?" instead of being matched. It runs after the search, so a choice the search offers stays a choice. A kind names the document ("registration certificate").
2. **Several needs.** If the message contains several needs ("EPF and EPS", "compare A with B"), `qwen3:8b` extracts up to `MAX_NEEDS` = 3. Each need is identified separately, and an optional relation question is answered by `/api/relation`.
3. **Ranking.** Each procedure scores by its best chunk's cosine similarity. `classify` returns:
   - **matched** when exactly one procedure clears 0.53 and is within 0.03 of the best;
   - **ambiguous** when several do;
   - **no_match** when none do.
4. **Abbreviations.** An abbreviation that names exactly one nearby procedure decides it ("EPS", "DL"). On a near miss, a term used by exactly one page overall ("VVPAT") decides it, if that page scores at least 0.45.
   - **Since 27 Oct:** a term written inside a longer name ("PAN" in "Link PAN with Aadhaar") names that procedure only when the question also uses another word of the name ("linking PAN with Aadhaar"). The same holds for the `named` flag. Initials ("DL") and a bracketed short form ("(EPS)") are unchanged. **Since 28 Oct:** a one-letter piece of a name (the "e" of "e-PAN") is not a word of it, so "e-filing" does not name "Instant e-PAN" (`11` #56).
   - **Since 27 Oct:** when the question uses such a term, a page whose name does not contain it is accepted only if the question's abbreviations or words name that page. The e-Filing login page only uses the PAN, so "apply for a new PAN card" is not matched to it, but "register on the e-filing portal with my PAN" is. A need phrase is checked together with its standalone question ("get a duplicate" / "… PAN card?").
   - **Since 27 Oct (`21`):** a lower-case word that is a stored procedure's own abbreviation is read in capitals ("idp" → "IDP", "eps" → "EPS"). A name's own abbreviations are the starts of its words' initials, or abbreviations written in it. A name that already holds one gives no initials, so "lpa" is not "Link PAN with Aadhaar".
5. **Name check.** At least half of the capitalised names in the question must appear in the page's text.
   - **Since 25 Oct (`19`, P0-2):** "US" and "UK" count as names and must appear as written, so "How do I apply for a US passport?" no longer matches the Indian passport page.
   - **Also since 25 Oct:** a name that abbreviates the candidate's own name or jurisdiction counts as found ("IDP").
   - **Code words:** a code word ("REV-101") gives no initial when abbreviations are matched (P1-2).
   - **Since 27 Oct:** "uk" counts in any case (lower-case "us" stays a word).
   - **Since 27 Oct:** India, its states and territories, and where the citizen lives, works, studies or travels ("I work in Dubai", "travelling to the UK") are not names the page must use. A state is still checked against a state procedure's jurisdiction (`covers`); a place that qualifies the service ("a UK driving licence") still counts.
   - **Where the citizen is (27 Oct, `21`).** Two nearby procedures for one service, one of them for citizens abroad (its name says overseas/NRI, as in "Overseas (NRI) Voter Registration" beside "Register to Vote"), are decided by the message, but only once the service itself clears the threshold:
     - the citizen says they are abroad ("abroad", "NRI", "outside India", or any foreign country or region, in any capitalisation) → the overseas procedure;
     - the message says nothing about where they are → the other;
     - a place the code cannot place (a city such as Dubai or Chennai) → the scores and the choice rules decide.
   - **A more specific document (27 Oct, `21`).** When every heading of the matched page that names the asked document adds qualifiers the question lacks ("Inter Caste Marriage Certificate" for "a marriage certificate"), the page is not matched. A page without headings says nothing here.
6. **Named-page tie rule (new, 23 Oct 2026).** In a close call, choose the one candidate that all four conditions pick out:
   - every other candidate's text names it;
   - it names none of them;
   - the question uses every word of its name;
   - exactly one page qualifies.

   Example: "International Driving Permit" against the fee table that lists "Issue of International Driving Permit". That page's "Fees as prescribed" is completed from the fee table (2.6). Anything else stays a choice for the citizen.
7. **Phrase versus question.** The extracted need phrase is tried first, then the standalone question, then the whole message. If the phrase matches one page but both other texts agree on another ("I live abroad"), the citizen chooses.
   - **Since 27 Oct:** the citizen also chooses when the whole message alone confidently matches another page. The extraction can drop what decides the service from both the phrase and its question ("I am an NRI", "I turned 18").
   - **Since 27 Oct (`21`):** the citizen also chooses when the standalone question confidently matches another page that the whole message also finds plausible ("i work in dubai, can i vote in india").

### 2.3 Retrieval
`retrieve` returns the five chunks of the chosen procedure closest to the question.
- **Row-group continuation (25 Oct).** If one of them ends with a numbered table item ("4. Issue or renewal of certificate of registration …:"), and the question uses two words of that item, the following chunks that start with exactly that item come too. Only the Rule 81 fee table (page 39) has such items.

### 2.4 Answer generation
- `build_guidance_prompt` gives `qwen3:8b` the passages as untrusted data, numbered by chunk ID.
- **It asks for:**
  - short ordered claims, each with a word-for-word quote and its chunk ID;
  - steps in official order from the first step, keeping who does each step;
  - fee claims stating the amount and what it is for;
  - the conditions kept with each fact;
  - nothing about other services or other kinds of applicant;
  - `insufficient_evidence: true` when the passages don't answer.

### 2.5 Verification (`rag.verify_claims`, deterministic)

A claim is kept only if all of these hold:

1. **The quote is real.** It appears word for word in the cited passage (punctuation and case ignored), and the passage is one of the retrieved chunks.
2. **The quote is long enough.** It has at least 4 words, or it is a whole list item without digits ("Insurance certificate*").
3. **Numbers match.** Every number in the claim equals a number in the quote, by value: Rs. 200 = Rs. 200.00/-, but not Rs. 20 and not 2.5 lakh. Ages, deadlines and counts written in words before a unit count too ("twenty years" = 20 years; added 24 Oct).
   - **Identifiers are names, not numbers (25 Oct).** "ITR-1", "Form 6A", "Form 30", "rule 81" and "Step 3" (`IDENTIFIER`) are left out of the number comparison.
   - Each identifier the claim names must instead appear in the quote, or in the heading the quote sits under.
   - So "ITR-1" is no longer read as the number 1, "Form 30" can no longer back a 30-day deadline, and "Form 6A" is no longer taken for "Form 6".
4. **No amount is dropped.**
   - Every amount of money in each whole sentence or table row the quote is cut from must appear in the claim, in figures or words ("Rupees One Thousand", "Twenty thousand rupees").
   - This stops "an additional fee of Rs. 300" that drops the row's extra Rs. 1,000 a year.
   - Separate sentences of a paragraph stand alone ("Minimum benefit: ₹2.5 lakh.").
   - If the claim is only a row's label copied without its fee, the official row itself is shown.
5. **Negation is kept.** The claim and the quote agree on negation (not, no, never, cannot, without).
6. **No back-reference (new).** A quote may not open with a back-reference such as "In such cases…" or "In that case…". It depends on the previous sentence, which must then be quoted too. Example: "In such cases a fee of Rs. 30/- will be realised" alone drops its condition, "more than 30 days after expiry".
7. **Same kind of document (new; RC/DL added 25 Oct: an amount claimed for an "RC" or a "DL" must come from a row about a registration certificate or driving licence).** If the claim names a kind of document ("registration certificate", "certificate of registration", "learner's licence", "income certificate"), that word must appear in the quote or in the question or lead-in the quoted paragraph sits under. A trade-certificate fee is never reported as a registration-certificate fee.
8. **Periods keep their unit and condition (25 Oct, `19` P1-1).** A claim keeps every period (number with year, month, week or day) its quote states, and adds none from outside the quoted sentence: "three days" is not "three months", and "for three months" keeps "within thirty days" when both are quoted. A quote cut short before its condition is not caught.
9. **Yes/No answers (25 Oct).** A quote cut from an answer opening with "Yes" or "No" includes that word. A bare "Yes" or "No" counts only directly under its question; on approved data that blocks "Apprentices can become EPF members" ← "Yes".
10. **Fee service (25 Oct).** An amount claimed for a "test", "duplicate" or "renewal" must come from a row (or the heading directly above it) saying so. The certificate-of-fitness fee is not "the fitness test fee".
11. **No duplicates.** Repeated claims are dropped.

### 2.6 Meaning check, applicant type and completion
- **Meaning check (`check_claims`).** `qwen3:8b` re-reads the surviving claims against their passages (same meaning, same amount for the same thing, conditions kept, right service and applicant, a fact rather than a link). It also says whether the claims fully answer the question.
- **Applicant type (`_for_the_asker`, deterministic).** A claim whose quote limits it to an organisation ("licence **to a school or establishment**") is dropped unless the question names that kind of applicant. A citizen asking about their own duplicate licence never gets the driving-school fee.
- **Completion (`answer_from_naming_pages`).** If the answer is not complete, another approved page that names this procedure is searched: only its passages naming the procedure are used, e.g. the fee table for "Fees as prescribed". Those claims carry that page's own ID and link.
  - **A fee question needs an amount (25 Oct).** In `_checked_answer`, a question about a fee or cost (`ASKS_FEE`) whose claims state no amount and do not say the service is free (`FREE`) is never complete, even if the model says so. So "Fees as prescribed" always leads to the fee table, and is flagged partial if no page states the amount.
  - **Only this procedure's rows (25 Oct).** Claims from the naming page are kept only if their quote or source row uses the procedure's name (`uses_name`), so "And how much does it cost?" on the IDP page gets the IDP row (Rs. 1000) and not the table's other rows.
- **Partial answers.** The response is flagged `partial` when claims exist but the check judged them incomplete. If no claim survives, the response is `insufficient_evidence` and the UI says the official page does not answer it.

### 2.7 Relation and comparison
`/api/relation` and comparisons use the same prompt and checks with stricter task rules: only quote sentences that themselves state the relationship, and one procedure per claim.

## 3. What the model is trusted with, and what it is not

| Trusted (and checked) | Never trusted |
|---|---|
| Choosing which passage answers | Numbers, amounts or negation that differ from the quote |
| Paraphrasing a quoted fact | Facts with no word-for-word quote |
| Judging meaning and completeness, as a second filter | Applicant-type limits (code checks them) |
| Rewriting Tamil into an English query (shown to the citizen) | Choosing between close procedures when no rule settles it (the citizen chooses) |

## 4. Known weaknesses of the logic (see `10_PENDING_WORK.md`)
- **Exact quoting by the 8B model.** It sometimes quotes inexactly ("The applicant" for "An applicant") or quotes only part of a fee row. Verification correctly rejects these, so the result is an abstention, not a wrong answer.
- **Meaning check.** It is a model and has approved wrong claims. That is why each class of error found in audits has been given a deterministic rule.
- **Retrieval.** It takes five chunks by similarity, so a long fee table can hide the right row: e.g. motorcycle RC renewal on the Rule 81 fee page. Fixed on 25 Oct for questions that reach page 39 (row-group continuation).
- **Identification has no model of intent or jurisdiction.** Wording similarity, the name check and the rules above decide. Since 27 Oct, PAN changes and new PAN cards no longer match a PAN page, and citizens abroad reach the overseas voter page. "Marriage certificate" is not matched on staging (page 17's heading names an Inter Caste Marriage Certificate). On approved data page 17 has no headings, so it is still matched there until page 17 is deleted (owner decision of 27 Oct; `19` checklist); its answer abstains and no card is shown. The answer model sometimes declines a question that states a foreign residence (2 of 8 overseas phrasings, `21`).
- **Abbreviations need the page in the top 3 (28 Oct).** The abbreviation override looks only at the 3 best-scoring pages (scoring at least 0.45). A growing collection can push the named page out: lower-case "how do i get an idp" lost its match when the PCC page was added. It falls back to no match.
- **No model of document type.** Tamil Nadu certificate questions without a stored page (marriage, widow, nativity, property) are identified as Registration of Births and Deaths (28 Oct). They abstain and show no card, because of the card rule and the document-kind rule.
- **Model calls (25 Oct).** `extractor.ollama_post` logs each call. It retries once for a dropped connection, a 5xx, or (embeddings) a 400; a timeout is never retried.

## 5. Ingestion stages and their failure handling
| Stage | Code | Failure handling |
|---|---|---|
| URL validation | `scraper.require_official` + `validate_url` | Official domains only (also after redirects); only http/https on public IPs, including the address actually connected to; rejected → 422 |
| HTTP fetch | `fetch_static_html` (httpx, 20 s, one retry on connection reset, ≤10 redirects re-validated, 2 MB cap, HTML content types only) | Timeout or 5xx → 502; 4xx, wrong type or too large → 422 |
| JavaScript pages | `fetch_rendered_html` (Playwright Chromium, sub-requests to private addresses blocked) | Used only when the static text is unusable; failures → 502 or 422 |
| Cleaning | `clean_html` (see 1) and `is_source_text_usable` (at least 200 characters and 20 words, not a placeholder) | "No meaningful page content" → 422 |
| Structured extraction | `extractor.build_extraction_prompt` + `call_qwen` (Ollama, JSON) | The prompt treats the source as untrusted data, uses only stated facts, keeps the step order and allows null for unknown fields |
| Schema validation | Pydantic `ProcedureExtraction` (strict; name ≤300, summary ≤5,000, eligibility ≤10,000, limited number of steps) | Invalid JSON or schema → 502 "invalid structured data"; the admin submits the URL again |
| Human review | Admin edits every field and sees the scraped text | — |
| Approval | Provenance token (HMAC over URL + text) → `build_chunks` → one transaction | Tampered text → 422; embedding failure → 502, nothing saved; duplicate URL → 409 |

**The model's draft is never saved by itself.** Only the approval endpoint writes, and only with a valid admin session and token.

## 6. Embedding consistency and when to regenerate
- **One rule:** chunks and embeddings are derived data, built from `source_text` at approval. They must always equal `chunk_text(source_text)` embedded with the configured model.
- **Regenerate when:**
  - the embedding model or `EMBEDDING_DIMENSIONS` changes (all pages; the column is `vector(1024)`);
  - the chunker changes (pages whose chunks differ);
  - a page is re-scraped (through re-approval).
- **Do not:** mix vectors from two models; they are not comparable.
- **Check with:** a fresh embedding of each chunk should have cosine ≈ 1.0 with the stored one. This held for all approved chunks on 23 Oct.

## 7. Other AI functionality
- **Follow-ups (changed 25 Oct; `CitizenPage.answerFollowUp`).**
  - The follow-up is identified first.
  - If it **names** a different procedure, that procedure answers it: its own abbreviation ("What about EPS?") or every word of its name ("How do I register to vote?"); `/api/identify` returns `named: true`, from `procedure_search.names_procedure`.
  - Otherwise the open procedure answers. A different procedure that merely matches answers only when the open page cannot.
  - Related words never move a follow-up: "What about the pension?" on EPF, and "What about the certificate?" on RC renewal (which matches an unrelated TN FAQ), both stay.
- **Cross-procedure answers.** Completion from a page naming the procedure (2.6); relation and comparison across procedures (2.7); several needs in one message (2.2).
- **Voice** (`backend/speech.py`). Indic-Transcribe Flex, a 1.2B-parameter model licensed under the Indic Open Model License, downloaded from Hugging Face after accepting its conditions:
  - it is loaded on the first recording and reused, one transcription at a time;
  - only WAV is accepted, at most 30 s; the file is written to a temporary file only for the model and then deleted;
  - transcripts and audio are not logged;
  - without the model, the endpoint answers "not set up".
- **Editable transcript.** The text goes into the question box; the citizen corrects it and presses Send.
- **Read aloud.** The browser's `speechSynthesis` with local voices only.
- **Answer language.** Answers are English (verified quotes from English pages). Tamil questions are answered in English, and the "Searched as" line shows the English query.
