# 01 — Project overview

## What ProcedureAssist is

ProcedureAssist turns official Indian government web pages into reviewed procedures and lets
citizens ask questions about them in plain English, Tamil, Romanized Tamil or a mix. Every
answer is a list of short claims. Each claim quotes the official page word for word and links
to it. When the approved pages do not answer a question, the app says so instead of guessing.
It gives guidance only; it never submits applications.

There are two kinds of user:

| User | Page | What they do |
|---|---|---|
| Admin (reviewer) | `/admin` | Signs in, pastes an official URL, reviews what the local model extracted (name, department, summary, steps, eligibility), corrects it and approves it. Approval saves the procedure and indexes its page text for search and quoting. |
| Citizen | `/` | Describes a situation or asks a question, sees the matching procedure (or chooses between close matches), reads its steps and official link, and asks follow-up questions. Can type or speak (Tamil or English). |

## What it is not

- It is not a chatbot that answers from general knowledge. The model may only restate what an
  approved page says, and code checks every quote.
- It is not a portal for applying or paying.
- It does not read PDFs or pages behind logins (HTML only).

## Technology (all local)

| Part | Technology |
|---|---|
| Backend | Python 3.14, FastAPI, SQLAlchemy |
| Database | PostgreSQL 16 with the pgvector extension |
| Models (via Ollama) | `qwen3:8b` (extraction, normalisation, answers, checks); `qwen3-embedding:0.6b` (1024-dimension search vectors) |
| Speech (optional) | Indic-Transcribe Flex (bodhan-ai), runs on the CPU inside the backend |
| Scraping | httpx + BeautifulSoup, Playwright Chromium for JavaScript pages |
| Frontend | React 19, TypeScript, Vite, Vitest |

## Current state in one paragraph (27 Oct 2026, evening)

The application works end to end on a laptop:
- admin review and approval;
- citizen identification, with clarification and choice;
- multilingual questions and voice input;
- verified answers with citations, and follow-ups.

The approved database holds 24 official pages. The scraper, chunker, answer checks and identification were repeatedly fixed and measured between 23 and 27 Oct, all uncommitted.

A corrected copy of the data is staged in `procedureassist_staging`. **It has not been applied to the approved database**, because that needs the owner's explicit approval. In it, page 17 (the e-Sevai FAQ, which misleads certificate questions) is deleted by the owner's decision; the copy holds 25 pages.

Five new official procedures were delegated to Claude for review and approval:
- four (N1, N3, N4, N8) are reviewed but not yet tested or approved;
- one (N10) is deferred.

See `00_START_HERE.md` (state and reading order), `10_PENDING_WORK.md` and `21_AUTONOMOUS_EXECUTION_STATE.md`.

## From an official page to an approved procedure
| State | What it is | Stored where | Who controls it | Citizens see it? |
|---|---|---|---|---|
| **Official source** | An HTML page on an allowed official domain (`OFFICIAL_SOURCE_DOMAINS`; default `gov.in`, `nic.in`, `pfrda.org.in`), checked before the first request and after redirects | The government website | The department | Only through the link on an approved card |
| **Extracted draft** | `POST /api/admin/extract`: the cleaned page text (paragraphs), the model's draft card, a provenance token (valid 2 hours) | Nowhere: only the admin's browser | The model drafts; nothing is saved | No |
| **Reviewed card** | The draft after the admin corrects name, department, jurisdiction, summary, eligibility and steps. The scraped text itself cannot be edited | The admin page's memory | The human reviewer | No |
| **Approved procedure** | `POST /api/admin/procedures`: the token proves the text is what was scraped. The card and the exact text are saved; the text is chunked and embedded in the same transaction | `procedures` row + `procedure_chunks` rows (1024-dimension vectors) | Saved only with an admin session and a valid token | **Yes:** identification and answers use only these |

- **No status column:** a stored procedure is approved.
- **Deleting it** (admin list, `DELETE /api/admin/procedures/{id}`) removes its chunks by cascade.
- **To change a stored procedure**, the reviewer deletes it and approves the page again. There is no edit route, and Re-extract was removed on 26 Oct.

## Generalisation goal
Any suitable official HTML page that was never seen before must work after the normal Extract → review → Approve, with no page-specific code.
- **Verified** by `scripts/evaluate_ingestion.py` on 6 unseen official URLs: PMSBY, PCC, Krishnagiri birth registration, Instant e-PAN, NPS and the TN ration card. It goes through the real routes, model and embeddings in a rolled-back test transaction: 37/37 checks on 27 Oct, run 2.
- **Identification rules** use reference data (states, countries) and the stored names only; no question-to-page mappings.

## Motivation and problem statement
Government procedure information in India is official but hard to use:
- it is spread across ministries' sites (Parivahan, ECI, UIDAI, Income Tax, EPFO, India Post, Passport Seva, state e-Sevai portals);
- it hides behind menus, accordions, tables and PDFs;
- it is written in English, while many citizens think and speak in Tamil or Tamil-English.

General chatbots fill the gaps with plausible but unverified fees and rules. The goal is an assistant that is *useful* (it finds and explains the right procedure) and *trustworthy* (it never states what the official page does not say).

## Objectives
1. Ingest official procedure pages through human review.
2. Identify the procedure a citizen means from a free-text situation, including several needs in one message.
3. Answer questions only with verified, cited facts, and abstain or clarify otherwise.
4. Support Tamil, Romanized Tamil and mixed input, typed or spoken.
5. Run fully locally, at low cost and with privacy (no citizen data sent to cloud services).

## Functional requirements (implemented; verified by tests unless noted)
| Requirement | Status |
|---|---|
| Admin login; only admins can extract, approve or delete | Implemented and tested (`test_auth.py`, `test_routes.py`) |
| Extract a draft procedure from an official URL; nothing saved until approval | Implemented and tested |
| Re-extract a draft from the same text | **Removed 26 Oct 2026** at the owner's request: a reviewer who wants a new draft submits the URL again. The provenance token still prevents text substitution at approval. |
| Approve: save procedure + chunks + embeddings atomically; reject duplicate URLs | Implemented and tested (`test_save.py`, `test_rag.py`) |
| List and delete procedures | Implemented and tested |
| Citizen: identify procedure(s), choose between close matches, ask for clarification when nothing is named | Implemented and tested (`test_identify.py`) |
| Citizen: verified answers with per-claim quotes and links; partial flag; abstention | Implemented and tested (`test_guidance.py`, `test_end_to_end.py`) |
| Follow-up questions on the open procedure, falling back to a new search | Implemented and tested (frontend `CitizenPage.test.tsx`) |
| Multiple needs and how they relate | Implemented and tested |
| Tamil, Romanized and mixed normalisation | Implemented and tested with mocks; measured with the real model on 36 questions (`tamil.json`) |
| Voice input (local speech model), editable transcript, read-aloud | Implemented and tested with mocks. Real model tried only on synthetic voices; **Tamil speech never tested** (no Tamil voice on this Mac) |
| Identification rules of 26–27 Oct: state jurisdiction, where the citizen lives (overseas vs ordinary voter), lower-case abbreviations, "Which certificate…?", a more specific document, PAN actions | Implemented and tested (`test_identify.py`); measured in `20`, `22` |
| Card rule: a procedure the citizen did not name is shown only with a verified answer from it | Implemented and tested (`CitizenPage.test.tsx`); modelled by `scripts/evaluate_answers.py` |
| Database outage during operation → 503 with a message and request id | Implemented and tested (`test_health.py`); exercised live 27 Oct (`evidence/test_results/p7_ops/`) |
| Database down at start-up | **Not handled:** the backend cannot start (tables are created on import) |

## Non-functional requirements
| Requirement | Status |
|---|---|
| Correctness over coverage: no unsupported claims | Enforced by deterministic checks. Latest suite (`p7_final`, 27 Oct): 0 citation failures and 0 unsupported claims. But **approved data still gives 2 wrong document lists and staging 1 misleading card, all from page 17**, which is removed by the planned deletion (owner approval pending) |
| Local and private | Everything is local; audio and transcripts are not stored or logged; question text is never logged |
| Security | Signed admin session (12 h), not revocable; 5 failed sign-ins per address per 15 min; SSRF protections and an official-domain allow-list on scraping; CORS restricted to `FRONTEND_ORIGIN`. DNS rebinding not prevented for a rendered page's scripts and styles |
| Response time | Median about 5–7 s per question, 40 s worst case (laptop, `qwen3:8b`); 20 simultaneous identify requests all succeeded (median 0.3 s) |
| Maintainability | Small codebase: about 2,700 lines of backend and 1,500 of frontend source (plus 800 of CSS); every rule has tests (252 backend, 67 frontend) |

## Scope
- **In scope:** HTML pages from official Indian government sites; guidance only.
- **Out of scope:**
  - PDFs, logins, payments and application submission;
  - answers in Tamil (answers are English quotes);
  - production hosting.

## Evolution: initial concept vs current implementation
- **Initial concept (Sep 2026).** Scrape a government page and have an LLM turn it into structured steps for citizens (commits "Add web scraper", "Add Qwen extraction client", "Add procedure saving").
- **Mid Oct 2026.**
  - It became clear that LLM-written steps alone are not trustworthy. The design moved to *retrieval-augmented answers with verified quotes*: pgvector chunks, the identify endpoint, follow-up answers from evidence, the negation check.
  - Admin authentication, provenance tokens and hardening followed.
  - The MVP was tagged on 16 Oct.
- **Late Oct 2026.**
  - Voice input.
  - Multilingual normalisation.
  - Reliability audits that added deterministic rules each time the model's own checks failed: applicant type, money, abbreviations.
- **23 Oct 2026.** A source audit showed that the remaining risk lay in the *data* (scraping losses), not only in the model. This led to the scraper, chunker and verification fixes, a staging database, and the pending migration.
- **24–25 Oct 2026.** RAG reliability audits added deterministic rules each time the model's own check failed:
  - identifiers vs quantities;
  - follow-up routing by naming;
  - fee completeness;
  - fee-table row groups;
  - periods, bare Yes/No and fee services.

  They also added a permanent safety evaluation set, logging and security hardening (`12`, `18`, `19`).
- **26 Oct 2026.** Generalisation and simplification (`20`):
  - Re-extract removed;
  - state jurisdiction taken from metadata;
  - browser fallback for servers the direct fetch cannot reach;
  - 11 new official candidates prepared.
- **27 Oct 2026.**
  - Identification of residence, abbreviations and documents; the honest no-answer card rule; a database-outage message (`20`, `22`).
  - The owner then decided to **delete page 17** and delegated the review and approval of five candidates. Its execution was interrupted for a fresh-account handoff (`21`).
