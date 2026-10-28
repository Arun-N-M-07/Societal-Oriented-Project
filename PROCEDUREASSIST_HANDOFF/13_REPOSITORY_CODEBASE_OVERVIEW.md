# 13 — Repository and Codebase Overview (inspection only)

Written for: the new technical owner of ProcedureAssist who needs a factual map of the code.

Basis: every statement below comes from reading the source in the working tree on branch `arun-nm` (which has uncommitted changes, see §9). Nothing was run, installed, connected to or modified. `.env` was read for key names only; no values are reproduced.

Status labels used throughout: **Implemented** (code present and wired end to end), **Partial** (code present, with a gap named), **Unverified** (code exists but this inspection could not confirm it works, because that needs a live DB, Ollama or model weights).

---

## 1. Repository overview

ProcedureAssist is a two-process web app. A FastAPI backend (`backend/`) lets an admin scrape an official government web page, have a local Qwen model draft a structured procedure from it, review and approve it, then stores the page text as embedded chunks in PostgreSQL + pgvector. A React/Vite frontend (`frontend/`) serves two UIs from one bundle: a citizen chat page at `/` and an admin page at `/admin`. Citizens ask questions in English or Tamil (typed or spoken); the backend finds the matching procedure by embedding similarity and answers with claims that must be quoted word-for-word from the stored official text.

All models run locally through Ollama (`qwen3:8b` for generation, `qwen3-embedding:0.6b` for embeddings). Optional speech-to-text uses a local Hugging Face model (`bodhan-ai/indic-transcribe-flex`).

Top-level layout and purpose:

| Path | What it actually is |
|---|---|
| `backend/` | The whole Python backend (13 files, ~2,250 lines). Entry: `backend/main.py` |
| `frontend/` | React 19 + TypeScript + Vite app. Entry: `frontend/index.html` → `src/main.tsx` |
| `tests/` | Python `unittest` suite (about 209 `def test` functions in 14 test modules + `db_support.py` helper) |
| `scripts/` | Four operator scripts: batch approval and three evaluation harnesses |
| `fixtures/` | JSON/text data for evaluation scripts, ingestion batch and a sample procedure |
| `PROCEDUREASSIST_HANDOFF/` | Untracked handoff docs `00`–`12` plus `evidence/` (audit logs, DB schema dumps, traces). This report is `13` |
| `start.sh`, `run.sh` | Startup scripts (§5) |
| `README.md`, `DEMO.md` | Setup/runbook docs |
| `Demo websites.txt`, `test_websites_and_questions.txt`, `How to run the website` | Plain-text scratch notes: URL lists, test questions, one-line "run `./start.sh`" |
| `requirements.txt`, `requirements-speech.txt` | Python deps (core / optional speech) |
| `package.json` (root) | Only defines `npm start` → `./run.sh`. No dependencies |
| `.env`, `.env.example`, `frontend/.env.example` | Config. `.env` is git-ignored (keys present: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD_HASH`) |
| `.claude/launch.json` | Claude Code launch configs for backend (port 8000) and frontend (port 5173) |
| `.gitignore` | Ignores `__pycache__`, `.venv`, `node_modules`, `dist`, `.env*` (except `.env.example`), `.DS_Store` |

**Generated / dependency / excluded directories (not part of source):** `.venv/` (Python virtualenv), `frontend/node_modules/`, `frontend/dist/` (Vite build output: `index.html`, `assets/index-*.js`, `assets/index-*.css`), `**/__pycache__/` (in `backend/` and `tests/`), `.git/`, `.DS_Store` files. None of these is tracked by git.

**No Alembic or migration tooling exists** (searched for it). Schema creation is `Base.metadata.create_all` (§6).

---

## 2. Complete source directory tree

```
SOP/
├── backend/
│   ├── auth.py               # passwords, session cookie, provenance tokens
│   ├── config.py             # env loading and settings
│   ├── database.py           # engine, session, read-only dependency
│   ├── extractor.py          # Ollama generate client + procedure extraction
│   ├── main.py               # FastAPI app, CORS, create_all
│   ├── models.py             # Procedure, ProcedureChunk
│   ├── normalize.py          # Tamil/Tanglish → English query
│   ├── procedure_search.py   # procedure identification, multi-need splitting
│   ├── rag.py                # chunking, embeddings, answer generation + verification
│   ├── routes.py             # all HTTP endpoints
│   ├── schemas.py            # Pydantic request/response models
│   ├── scraper.py            # SSRF-safe fetch, Playwright fallback, HTML→text
│   └── speech.py             # local Indic-Transcribe speech-to-text
├── frontend/
│   ├── index.html            # mounts #root, loads src/main.tsx, src/styles.css
│   ├── package.json          # scripts: dev, build, preview, test
│   ├── tsconfig.json
│   ├── vite.config.ts        # react plugin + vitest (jsdom). No proxy, no server block
│   ├── .env.example          # VITE_API_BASE_URL
│   └── src/
│       ├── main.tsx          # createRoot → <App/>
│       ├── App.tsx           # path-based router: /admin* → AdminApp else CitizenPage
│       ├── api.ts            # fetch wrapper + typed API functions
│       ├── CitizenPage.tsx   # citizen chat UI
│       ├── VoiceInput.tsx    # mic recording → WAV → transcribe
│       ├── AdminLogin.tsx
│       ├── AdminPage.tsx     # URL → extract → review → approve
│       ├── AdminProcedureList.tsx
│       ├── styles.css        # 795 lines, single stylesheet
│       └── *.test.ts(x)      # 6 Vitest files (see §4)
├── tests/                    # db_support.py + 14 test_*.py
├── scripts/                  # approve_batch.py, evaluate_{answers,identification,needs}.py
├── fixtures/
│   ├── evaluation/           # answers, demo_services, heldout (untracked), identification, multi_need, population, tamil (.json)
│   ├── ingestion/demo_batch.json
│   ├── sample_procedure.json
│   └── sample_source_text.txt
├── PROCEDUREASSIST_HANDOFF/  # docs 00–13, evidence/{audit_reports,database,evaluations,investigations,other,source_audits,test_results,traces}
├── start.sh  run.sh  package.json
├── requirements.txt  requirements-speech.txt
├── README.md  DEMO.md  Demo websites.txt  test_websites_and_questions.txt  "How to run the website"
├── .env  .env.example  .gitignore  .claude/launch.json
└── (excluded) .venv/  frontend/node_modules/  frontend/dist/  __pycache__/  .git/
```

---

## 3. Backend file-by-file breakdown

Dependency summary (project-internal imports): `main` → `routes`, `models`, `database`, `config`. `routes` → almost everything. `rag`, `procedure_search`, `normalize` all call `extractor.call_qwen`. `config` is the root imported by most modules.

### 3.1 `backend/config.py` — settings (infrastructure)
- Loads `<repo>/.env` with `python-dotenv` (`load_dotenv`) at import time. Raises `RuntimeError` at import if `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD_HASH` are missing, if `SECRET_KEY` < 32 chars, or if the hash does not start with `scrypt$`.
- Settings and defaults: `OLLAMA_BASE_URL` (`http://localhost:11434`), `LLM_MODEL` (`qwen3:8b`), `LLM_CONTEXT_TOKENS` (32768), `EMBEDDING_MODEL` (`qwen3-embedding:0.6b`), `EMBEDDING_DIMENSIONS` (1024), `FRONTEND_ORIGIN` (`http://localhost:5173`), `ADMIN_USERNAME` (`admin`), `COOKIE_SECURE` (false), `IDENTIFY_MIN_SCORE` (0.53), `IDENTIFY_MARGIN` (0.03), `MAX_NEEDS` (3), `SPEECH_MODEL` (`bodhan-ai/indic-transcribe-flex`), `SPEECH_MODEL_DIR` (optional).
- Used by: `database`, `models`, `extractor`, `rag`, `routes`, `procedure_search`, `speech`, `main`, `auth` (lazily).
- Side effect to know: importing any module that imports `config` fails without a complete `.env`. That is why `tests/db_support.py` sets env vars before importing backend modules.

### 3.2 `backend/database.py` — database access
- `engine = create_engine(DATABASE_URL)`, `SessionLocal = sessionmaker(autocommit=False, autoflush=False)`, `Base = declarative_base()`.
- `get_db()` — FastAPI dependency yielding a session, closed in `finally`.
- `get_read_only_db(db)` — depends on `get_db` and executes `SET TRANSACTION READ ONLY`, so PostgreSQL itself rejects writes on citizen routes.
- Used by: `routes.py`, `models.py`, `main.py`, `rag.py` (`__main__` backfill), scripts, tests. Deps: SQLAlchemy, FastAPI.

### 3.3 `backend/models.py` — database models
- `Procedure` (table `procedures`) and `ProcedureChunk` (table `procedure_chunks`); details in §7. Deps: SQLAlchemy, `pgvector.sqlalchemy.Vector`. Used by `routes`, `rag`, `procedure_search`, `main` (import registers tables).

### 3.4 `backend/main.py` — application entry point
- Imports `models` (to register tables), runs `Base.metadata.create_all(bind=engine)` at import, builds `FastAPI(title="ProcedureAssist")`, adds `CORSMiddleware` (`allow_origins=[FRONTEND_ORIGIN]`, `allow_credentials=True`, methods `GET/POST/DELETE`, header `Content-Type`), mounts `routes.router`. Run as `uvicorn backend.main:app`.

### 3.5 `backend/routes.py` — API handling (all endpoints)
Two routers: `router` (public) and `admin_router` (`dependencies=[Depends(require_admin)]`), merged by `router.include_router(admin_router)`.

| Method + path | Function | Auth | DB session |
|---|---|---|---|
| GET `/health` | `health` | none | none |
| GET `/health/ready` | `readiness` | none | `get_db` (checks `procedure_chunks`; calls Ollama `/api/tags`; 503 if not all ok) |
| POST `/api/admin/login` | `login` | none | none (sets cookie `admin_session`, httponly, samesite=strict) |
| POST `/api/admin/logout` | `logout` | none | none |
| GET `/api/admin/session` | `session` | `require_admin` | none |
| POST `/api/admin/extract` | `create_extraction` | admin | none |
| POST `/api/admin/re-extract` | `re_extract_procedure` | admin | none |
| POST `/api/admin/procedures` | `save_procedure` | admin | `get_db` (writes) |
| GET `/api/admin/procedures` | `list_saved_procedures` | admin | `get_db` |
| DELETE `/api/admin/procedures/{id}` | `delete_procedure` | admin | `get_db` |
| GET `/api/procedures` | `list_procedures` | none | read-only |
| GET `/api/procedures/{id}` | `get_procedure` | none | read-only |
| POST `/api/speech/transcribe` | `transcribe_speech` (async) | none | none |
| POST `/api/identify` | `identify_procedure` | none | read-only |
| POST `/api/guidance` | `guidance` | none | read-only |
| POST `/api/relation` | `relation` | none | read-only |

Helpers: `_verify_provenance`, `_summary`, `_normalized`. Constants `CLARIFY`, `WAV_TYPES`.
Imports from project: `auth`, `config`, `database`, `extractor`, `models`, `normalize`, `procedure_search`, `rag`, `scraper`, `schemas`, `speech`. Used by: `main.py` and `tests/db_support.py`.

### 3.6 `backend/schemas.py` — API contracts (Pydantic)
- `StrictModel` (`extra="forbid"`) base. Limits: `MAX_URL_LENGTH` 2048, `MAX_SOURCE_TEXT_LENGTH` 100,000, `MAX_STEPS` 100, `MAX_STEP_LENGTH` 2000. `Language = Literal["en","ta"]`. `_http_url` validator.
- Admin/ingestion: `ScrapeResult`, `ExtractRequest`, `ProcedureExtraction`, `ProcedureDraft`, `ReExtractRequest`, `ExtractionResponse`, `ApprovalRequest`, `SavedProcedureResponse`, `AdminProcedure`, `LoginRequest`, `AdminSession`.
- Citizen: `ProcedureSummary`, `ProcedureDetail`, `IdentifyRequest/Response`, `Need`, `PendingNeed`, `GuidanceRequest/Response`, `Claim`, `GuidanceClaim`, `RelationRequest/Response`, `RelationClaim`, `TranscriptionResponse`. Question max length 1000.
- Used by `routes`, `extractor`, `scraper`. Dep: pydantic.

### 3.7 `backend/auth.py` — admin authentication and provenance (API/security)
- `hash_password` / `verify_password`: scrypt (n=2^14, r=8, p=1), stored as `scrypt$n$r$p$salt$digest`. `check_admin_credentials` compares username and password in constant time.
- `create_session_token` / `require_admin`: stateless HMAC-SHA256-signed cookie value `session:<expiry>:<username>:<sig>`, TTL 12 h (`SESSION_TTL_SECONDS`). No server-side session store.
- `issue_provenance_token` / `verify_provenance_token`: signed token binding `sha256(source_url + "\n" + source_text)` with 2 h TTL (`PROVENANCE_TTL_SECONDS`). Proves the server extracted exactly this text from this URL; it does **not** check that the URL is a government domain (docstring says so).
- `python -m backend.auth` (`__main__`) prompts for a password (min 12 chars) and prints a hash for `ADMIN_PASSWORD_HASH`. `config` is imported lazily inside functions so this works before `.env` exists.

### 3.8 `backend/scraper.py` — ingestion: fetch and text extraction
- `scrape_url(url)` → `ScrapeResult`: `fetch_static_html` (httpx) → `clean_html` (BeautifulSoup); if `is_source_text_usable` fails (<200 chars, <20 words, or a "enable javascript/loading" placeholder under 500 chars) it falls back to `fetch_rendered_html` (Playwright headless Chromium), then `clean_html` again. `_result` rejects text >100,000 chars and normalizes the URL (`normalize_url`: strips trailing slash, fragment, `utm_*`).
- SSRF defences: `validate_url` (http/https only, no credentials, no localhost, resolves DNS and rejects any non-global address via `_is_public_address`), re-run on every redirect (manual redirect loop, max 10) and on every Playwright sub-request (`page.route`). Response size cap 2 MB (`_read_limited`), content-type must be HTML/XHTML. One retry on connection reset (`_get_with_retry`).
- Text cleaning: drops script/style/nav/header/footer/aside/hidden elements; prefers `main`/`[role=main]`; emits paragraph blocks (`_is_block`), table rows kept as one block with parent-row context (`_row_context`, for fee schedules), drops link-menu runs (`is_menu`).
- Errors: `ScraperError` (client, → HTTP 422) and `SourceUnavailableError` (upstream, → 502).
- Deps: httpx, bs4, playwright. Used by: `routes.create_extraction`, `scripts/evaluate_identification.py`.

### 3.9 `backend/extractor.py` — LLM client + procedure extraction
- `call_qwen(prompt)`: POST `{OLLAMA_BASE_URL}/api/generate` with `format:"json"`, `think:false`, `temperature:0`, `num_ctx=LLM_CONTEXT_TOKENS`, 60 s timeout; raises `ExtractionError` on timeout/HTTP/connection/empty response. **This is the single LLM entry point** used by `extractor`, `normalize`, `procedure_search`, `rag`.
- `build_extraction_prompt`, `parse_extraction` (validates into `ProcedureExtraction`), `extract_procedure(source_text, source_url)` → `ProcedureDraft`.
- Used by: `routes` (`create_extraction`, `re_extract_procedure`).

### 3.10 `backend/normalize.py` — Tamil / Tanglish query normalization
- `needs_normalizing(question, language)`: true if language is `"ta"`, or text has Tamil script (`TAMIL_SCRIPT`), or matches the `ROMANIZED_TAMIL` hint regex (a hand-written word list).
- `normalize_query(question)`: LLM call (`PROMPT` with examples) returning `{normalized_query, needs_clarification, clarification_reason}`; returns `None` on any failure/invalid shape (then the original question is searched).
- Used by: `routes._normalized` (called from `identify_procedure` and `guidance`).

### 3.11 `backend/procedure_search.py` — procedure identification (retrieval)
- `rank_procedures(db, vector)`: per procedure, max cosine similarity over its chunks (`func.max(1 - embedding.cosine_distance(vector))`), top `MAX_CANDIDATES`=3.
- `classify(ranked, min_score, margin)` → `matched` / `ambiguous` / `no_match` using `IDENTIFY_MIN_SCORE` and `IDENTIFY_MARGIN`.
- `_decide(db, vector, text)`: classify, then acronym rules (`ACRONYM`, `abbreviates`), a name-presence check (`mentions`, capitalised terms must appear in the page text), and `named_by_the_others` (resolve a close call toward the page that other candidates merely name).
- `identify(db, question, need=None)`: embeds phrase/standalone question/whole message and takes the first confident match; special case produces `ambiguous` when phrase and message disagree.
- `identify_needs(db, message)`: if `MULTI_HINT` matches, `extract_needs` (LLM, `NEEDS_PROMPT`, validated by `_from_message`) splits the message into needs; `COMPARED` regex handles "difference between A and B"/"A vs B"; each need is matched separately, same-procedure needs are merged, more than `MAX_NEEDS` go to `pending`. Returns a tuple `(results, pending, relation_question)` for multi-need, or a `[phrase, question]` list / `None` for the single flow.
- `names_something(question)`: false if the question has only generic words (`GENERIC_WORDS`), so `routes` replies with the `CLARIFY` text instead of searching.
- Imports: `config`, `extractor.call_qwen`, `models`, `rag` (uses `rag.embed_texts`). Used by `routes.identify_procedure`.

### 3.12 `backend/rag.py` — chunking, embeddings, answer generation, verification (RAG core)
- Ingestion side: `chunk_text` (1000-char chunks, 200 overlap, paragraph boundaries; restarts a chunk at the last heading when short — `_is_heading`), `embed_texts(texts, query=False)` (POST `/api/embed`; queries get `QUERY_INSTRUCTION` prefix; checks vector count/dimension; `EmbeddingError`), `build_chunks(source_text)` → unsaved `ProcedureChunk` list, `backfill(db)` (index procedures without chunks; CLI `python -m backend.rag backfill`).
- Retrieval: `retrieve(db, procedure_id, question, limit=5)` (cosine order within one procedure; `GUIDANCE_PASSAGES`=5, `RELATION_PASSAGES`=3).
- Generation: `build_guidance_prompt` (modes `answer`/`relation`/`comparison` via `TASKS`), `_ask` (JSON parse, errors → `GuidanceError`), `_answer`.
- Verification (deterministic code, not the LLM): `verify_claims` keeps a claim only if its quote appears word-for-word in the cited chunk (`_words`), meets a minimum length (`MIN_QUOTE_WORDS`=4 unless `_whole_item`), all numbers and amounts match (`_numbers`, `_money`, `_amount`), negation agrees (`NEGATION`), no `BACK_REFERENCE` opener, and document kind agrees (`_document_kinds`, `_section_heading`). Then `check_claims`: a second LLM pass (`CHECK_PROMPT`) returns which claims are correct and whether the answer is complete, followed by `_for_the_asker` (drops organisation-only fees, `APPLICANT_LIMIT`). `_checked_answer` chains these.
- Public entry points: `answer_question`, `answer_from_naming_pages` (complete "Fees as prescribed" from another page that names the procedure), `relate` (relationship claims; quote must contain `RELATION_TERMS` and name another procedure), `compare` (per-procedure comparison points), `COMPARISON` regex.
- Imports: `config`, `extractor`, `models`. Used by: `routes`, `procedure_search`, `scripts/*`.

### 3.13 `backend/speech.py` — speech workflow
- `transcribe(data, language)`: `check_audio` (16 kHz mono 16-bit WAV, 0.3–30 s, not silent: peak ≥ 200) → acquire module-level `_lock` (wait 30 s else `SpeechBusyError`) → `_load()` (lazy singleton; `huggingface_hub.snapshot_download(local_files_only=True)` or `SPEECH_MODEL_DIR`; inserts model dir into `sys.path` and imports `indic_transcribe.IndicTranscribe`; any failure → `SpeechUnavailableError`) → write temp WAV file → `model(path, lang=language, mode=MODES[language])` (`ta`→`mixed`, `en`→`native`) → delete temp file in `finally`. Output capped to 1000 chars.
- Exceptions: `AudioError`, `SpeechUnavailableError`, `SpeechBusyError`, `TranscriptionError`.
- Used by: `routes.transcribe_speech`. Heavy deps (`torch`, `transformers`, …) are only in `requirements-speech.txt` and imported lazily.

---

## 4. Frontend file-by-file breakdown

Stack: React 19.3.0, TypeScript, Vite 8, Vitest + Testing Library (versions in `frontend/package.json`). No router library, no state library, no UI library.

| File | Responsibility, key functions | Calls (api.ts) | Depends on | Workflow | Test |
|---|---|---|---|---|---|
| `src/main.tsx` | Renders `<App/>` in `StrictMode` into `#root` | — | `App` | all | — |
| `src/App.tsx` | `App`: `window.location.pathname.startsWith("/admin")` → `AdminApp`, else `CitizenPage`. `AdminApp`: `getSession` on mount, listens for `UNAUTHORIZED_EVENT` to drop to login with an expiry notice, `handleSignOut`; renders `AdminLogin` or `AdminPage` + `AdminProcedureList` (re-keyed by `savedCount` to refresh after save) | `getSession`, `logout` | `AdminLogin`, `AdminPage`, `AdminProcedureList`, `CitizenPage` | routing, admin | `App.test.tsx` (8) |
| `src/api.ts` | Base URL `import.meta.env.VITE_API_BASE_URL \|\| "http://localhost:8000"`. Private `request<T>` uses `fetch` with `credentials:"include"`, JSON or raw `Blob` body, dispatches `UNAUTHORIZED_EVENT` on 401 (except login/session paths), maps error `detail`. Exports typed functions below and all response types | `extractProcedure` (POST /api/admin/extract), `reExtractProcedure` (/re-extract), `approveProcedure` (POST /api/admin/procedures), `login`, `logout`, `getSession`, `listSavedProcedures`, `deleteProcedure`, `identifyProcedure` (/api/identify), `getProcedure` (/api/procedures/{id}), `askGuidance` (/api/guidance), `askRelation` (/api/relation), `transcribeSpeech` (/api/speech/transcribe?language=) | — | all | `api.test.ts` (5) |
| `src/AdminLogin.tsx` | Username/password form; `handleSubmit` calls `login`, clears password on error | `login` | `api` | admin auth | covered via `App.test.tsx` |
| `src/AdminPage.tsx` | Admin ingestion/review UI. State: URL, source text, provenance token, draft, step list with ids. `handleExtract`, `handleReExtract` (re-runs LLM on the same text with the token), `handleDiscard` (confirm), `handleApprove` (trims fields, requires name/summary/≥1 step, sends edited draft + original source text + token). Steps can be edited, added, removed, reordered by drag or ArrowUp/ArrowDown on the handle (`moveStep`). Source URL and source text are read-only | `extractProcedure`, `reExtractProcedure`, `approveProcedure` | `api` | admin review/approval | `AdminPage.test.tsx` (15) |
| `src/AdminProcedureList.tsx` | Lists saved procedures, Refresh, Delete (`window.confirm`) | `listSavedProcedures`, `deleteProcedure` | `api` | admin management | `AdminProcedureList.test.tsx` (5) |
| `src/CitizenPage.tsx` | Chat UI (545 lines). `handleSend` decides: first question → `identifyProcedure`; with an open procedure → `answerFollowUp` (answer from open procedure, and if `insufficient_evidence`, re-identify and answer from another matched procedure); with several matched procedures → `followUp` (answer from one, or relation check when `ASKS_RELATION` matches, else ask which). `handleResult` → `showAndAnswer` (single match: `getProcedure` + `askGuidance`) or `answerNeeds` (multi-need: one `askGuidance` per matched section, then `askRelation`). Ambiguous result renders "Choose" list (`openProcedure`). Renders claims with collapsible "Official source" quote + link (`renderAnswer`), partial/omitted notes, retry (`failure`, `run`). `ReadAloud` uses browser `speechSynthesis`, offline English voices only. Language `<select>` (en/ta); Enter sends. Shows "Searched as:" for normalized Tamil queries | `identifyProcedure`, `getProcedure`, `askGuidance`, `askRelation` | `api`, `VoiceInput` | citizen, voice, multi-need | `CitizenPage.test.tsx` (36) |
| `src/VoiceInput.tsx` | `toWav(blob)` decodes the browser recording with `OfflineAudioContext(1,1,16000)`, mixes to mono 16 kHz and writes a 16-bit WAV header manually. Component uses `getUserMedia` + `MediaRecorder`, 30 s cap with timer, cancel/stop, mic error messages, and puts the transcript in the question box via `onTranscript`; unsupported browsers show a note | `transcribeSpeech` | `api` | voice | `VoiceInput.test.tsx` (10) |
| `src/styles.css` | Single global stylesheet | — | — | all | — |

Test counts above are `it/test/describe` line counts from a grep, not run results.

---

## 5. Application startup flow

**`./start.sh`** (full local stack, macOS-specific):
1. `cd` to repo root; helper `setting()` greps `.env` for `OLLAMA_BASE_URL`, `LLM_MODEL`, `EMBEDDING_MODEL` (defaults match `config.py`), without sourcing the file.
2. `brew services start postgresql@16` (errors ignored).
3. If `GET $OLLAMA_URL/api/tags` fails: `nohup ollama serve` (log `/tmp/ollama.log`), wait until it answers.
4. Verifies both models appear in `/api/tags`; exits with a `ollama pull` hint if not.
5. Warm-up `ollama run $LLM_MODEL "hi"`.
6. Opens `http://localhost:5173` after 6 s, then `exec ./run.sh`.

**`./run.sh`**:
1. Requires `python3`, `npm`, and `.env`.
2. Creates `.venv` if absent; **runs `pip install -r requirements.txt` and `playwright install chromium` every time**; runs `npm install --prefix frontend --no-package-lock` only if `frontend/node_modules` is missing. (The task rules forbid installing in this inspection; I only read this.)
3. Checks the DB with `from backend.database import engine; engine.connect()`.
4. Starts `uvicorn backend.main:app --host 127.0.0.1 --port 8000` and `vite --host 127.0.0.1 --port 5173 --strictPort` (from `frontend/`) as background processes; a `trap` cleanup kills both on exit; the loop exits when either dies.

**Processes and ports:** PostgreSQL (default 5432, from `DATABASE_URL`), Ollama (11434), backend uvicorn (8000), Vite dev server (5173). The frontend is served by the Vite dev server only; there is no production static serving in the backend, and `frontend/dist` is just a build artifact.

**Frontend → backend:** the browser calls `VITE_API_BASE_URL` (default `http://localhost:8000`) directly (no Vite proxy; `vite.config.ts` has no `server` block). Cross-origin cookies work because CORS allows only `FRONTEND_ORIGIN` with `allow_credentials=True`. Consequence: the app must be opened at `http://localhost:5173`; `127.0.0.1:5173` is a different origin and fails CORS (README states this).

**Backend import-time behaviour:** `backend/main.py` imports `config` (needs `.env`), then runs `create_all`, which needs the DB reachable and the `vector` extension already installed (the app never executes `CREATE EXTENSION`).

**Environment variables:** loaded by `backend/config.py` via `python-dotenv` from `<repo>/.env` (real environment variables also work, since `os.getenv` is used and `load_dotenv` does not override existing variables). Frontend reads `VITE_API_BASE_URL` (optionally from `frontend/.env`).

---

## 6. Major workflow maps

Legend: **I** implemented, **P** partial, **U** unverified.

### 6.1 Administrator authentication — I
1. `AdminApp` (`App.tsx`) → `getSession()` → GET `/api/admin/session` → `routes.session` → `auth.require_admin`.
2. 401 → `AdminLogin.handleSubmit` → `api.login` → `routes.login` → `auth.check_admin_credentials` (→ `verify_password`) → `create_session_token` → `Set-Cookie admin_session` (httponly, SameSite=strict, `secure=COOKIE_SECURE`, 12 h).
3. All `admin_router` routes enforce `require_admin`. Expired/invalid cookie → 401 → `UNAUTHORIZED_EVENT` → login screen with notice.
4. Logout: `routes.logout` deletes the cookie (the token is stateless, so it is not revoked server-side).
- Gaps (also in README): no login rate limiting; no CSRF token (relies on SameSite=strict + CORS); only one admin account (`ADMIN_USERNAME` + hash in env).

### 6.2 Government URL submission — I
`AdminPage.handleExtract` → `api.extractProcedure` → POST `/api/admin/extract` → `schemas.ExtractRequest` (URL validator) → `routes.create_extraction`.

### 6.3 Scraping and extraction — I (live behaviour U)
`routes.create_extraction` → `scraper.scrape_url` → `fetch_static_html` (`validate_url`, redirect loop, `_read_limited`) → `clean_html` → `is_source_text_usable`; else `fetch_rendered_html` (Playwright) → `clean_html` → `_result`. Then `extractor.extract_procedure` → `build_extraction_prompt` → `call_qwen` → `parse_extraction` → `ProcedureDraft`. Response: `ExtractionResponse` with `source_text`, `procedure`, and `auth.issue_provenance_token`. No domain allow-list check that the URL is actually a government site exists (any public http(s) URL is accepted).

### 6.4 Human review and approval — I
`AdminPage` shows the draft; the admin edits fields/steps; optional `handleReExtract` → `/api/admin/re-extract` → `_verify_provenance` → `extract_procedure` (same source text, new LLM draft). `handleApprove` → `api.approveProcedure` → POST `/api/admin/procedures` → `routes.save_procedure`. Approval is a human action in the UI; there is no separate "pending/approved" status column. A saved row is immediately live for citizens. `scripts/approve_batch.py` is a CLI version of the same flow through the same endpoints (prompts for `y` per page).

### 6.5 Database storage — I
`routes.save_procedure`: `_verify_provenance(token, url, source_text)` (422 on mismatch/expiry) → `rag.build_chunks(source_text)` (chunk + embed **before** touching the DB; `EmbeddingError` → 502 "Nothing was saved") → create `Procedure` (`structured_data = {eligibility, steps}`) → `db.flush()` → set `chunk.procedure_id` → `db.add_all` → `db.commit()`. `IntegrityError` with pgcode `23505` → 409 (duplicate `source_url`); other errors → rollback + 500. Note the edited fields (name/summary/steps) are stored as structured data, but **chunks are built from the scraped `source_text`, not from the edited fields**.

### 6.6 Citizen question submission — I
`CitizenPage.handleSend` → `run(...)` → `api.identifyProcedure(question, language)` → POST `/api/identify`.

### 6.7 Procedure identification and retrieval — I (quality U; see evaluation docs)
`routes.identify_procedure`:
1. `_normalized` → `needs_normalizing` → `normalize.normalize_query` (Tamil only). If it needs clarification → `no_match` with `CLARIFY`.
2. `procedure_search.names_something` (generic-only question → `CLARIFY`).
3. `procedure_search.identify_needs` (LLM `extract_needs` only if `MULTI_HINT`; `COMPARED` regex) → either multi-need result, or
4. `procedure_search.identify` → `rag.embed_texts(query=True)` → `_decide` → `rank_procedures` (pgvector cosine on `procedure_chunks.embedding`) → `classify` + acronym/name checks.
5. Returns `IdentifyResponse` status `matched` | `ambiguous` | `no_match` | `multiple`. `EmbeddingError` → 502.
Frontend then: `matched` → `showAndAnswer`; `ambiguous` → choice list; `multiple` → `answerNeeds`.

### 6.8 Answer generation and verification — I (accuracy of answers U here; tied to Ollama)
`CitizenPage.answer` → POST `/api/guidance` → `routes.guidance`: load `Procedure` (404) → optional `_normalized` → `rag.answer_question` = `retrieve` (top 5 chunks) → `build_guidance_prompt` → `call_qwen` → `verify_claims` (deterministic) → `check_claims` (second LLM pass + `_for_the_asker`). If not `complete`, `rag.answer_from_naming_pages` may add claims from another page naming this procedure (those claims carry that page's `procedure_id` and `source_url`). Response `GuidanceResponse` with `insufficient_evidence` (= no verified claims), `omitted_claims`, optional `partial`. For several procedures: POST `/api/relation` → `routes.relation` → `rag.compare` (if `COMPARISON` regex matches) or `rag.relate`.

### 6.9 Voice input and transcription — P (U without model)
`VoiceInput.start` → `getUserMedia`/`MediaRecorder` → `toWav` → `api.transcribeSpeech` → POST `/api/speech/transcribe?language=` (Content-Type `audio/wav`) → `routes.transcribe_speech` (415 for wrong type, 413 for oversize while streaming, `asyncio.wait_for(run_in_threadpool(speech.transcribe), 120 s)`) → `speech.check_audio` → `_load` → model call → text returned to the question box for the citizen to edit. Error mapping: `AudioError`→422, `SpeechUnavailableError`→503, `SpeechBusyError`→503, `TranscriptionError`→502, timeout→504. Marked partial because it is optional: it only works if `requirements-speech.txt`, a gated Hugging Face model download and its custom `indic_transcribe` code are present; this could not be verified from source alone. `tests/test_speech.py` tests the logic with the model absent or mocked.

### 6.10 Other implemented workflows
- **Tamil / Tanglish handling** (`normalize.py`, `routes._normalized`) — I, LLM quality U.
- **Multi-need and comparison questions** (`procedure_search.identify_needs`, `rag.relate/compare`, `CitizenPage.answerNeeds`) — I.
- **Follow-up fallback** (`CitizenPage.answerFollowUp`) — I.
- **Delete procedure** (`routes.delete_procedure`; chunks removed by FK `ondelete=CASCADE`) — I.
- **Backfill indexing** (`rag.backfill`, `python -m backend.rag backfill`) — I.
- **Readiness check** (`routes.readiness`) — I.
- **Browser read-aloud** (`CitizenPage.ReadAloud`) — I; uses installed offline English voices only.
- **Evaluation harnesses** (`scripts/evaluate_answers.py`, `evaluate_identification.py`, `evaluate_needs.py`) — I as tools; results are in the handoff docs and not re-verified here.

---

## 7. Database architecture

Source: `backend/models.py`, `backend/database.py`, `backend/main.py`. No database was connected to.

**Tables**

`procedures`
- `id` Integer PK
- `name` Text NOT NULL
- `department` Text NULL, `jurisdiction` Text NULL
- `summary` Text NOT NULL
- `source_url` Text NOT NULL **UNIQUE** (duplicate-URL protection used by `save_procedure` → 409)
- `source_text` Text NOT NULL (full scraped text, ≤100,000 chars)
- `structured_data` JSONB NOT NULL — keys `eligibility`, `steps`

`procedure_chunks`
- `id` Integer PK
- `procedure_id` Integer NOT NULL, FK → `procedures.id` **ON DELETE CASCADE**, indexed
- `chunk_index` Integer NOT NULL; `UniqueConstraint(procedure_id, chunk_index)`
- `content` Text NOT NULL
- `embedding` `Vector(EMBEDDING_DIMENSIONS)` NOT NULL (default 1024, pgvector)

Relationship: one `Procedure` has many `ProcedureChunk`. There is no SQLAlchemy `relationship()`; joins are done by `procedure_id` queries. No users, sessions, audit-log, or status tables exist (admin identity lives in env vars).

**Vector storage and search:** embeddings from `qwen3-embedding:0.6b` via Ollama `/api/embed`; queries are prefixed with `QUERY_INSTRUCTION`, documents are not. Search uses `ProcedureChunk.embedding.cosine_distance(vector)` (`rag.retrieve`, `procedure_search.rank_procedures`). **No vector index (HNSW/IVFFlat) is declared in the models**, so searches are sequential scans (fine for a small corpus; I did not check whether one exists in the live DB, and `evidence/database/schema.txt` is the place to look).

**Connection architecture:** one global SQLAlchemy `engine` (default pool settings, `psycopg2`) and `SessionLocal(autocommit=False, autoflush=False)`. Sessions are request-scoped via `get_db` (closed in `finally`).

**Transactions:**
- Citizen routes use `get_read_only_db`, which issues `SET TRANSACTION READ ONLY` as the first statement, so PostgreSQL rejects writes.
- Admin writes: explicit `db.commit()` with `rollback()` on `SQLAlchemyError`; `save_procedure` does flush then commit in one transaction; embeddings are computed before opening the write (stated in `build_chunks` docstring).
- `readiness` uses plain `get_db`.

**Schema initialization:** only `Base.metadata.create_all(bind=engine)` in `main.py` (creates missing tables, never alters existing ones). `CREATE EXTENSION vector` is a manual step (README) and is done programmatically only in `tests/db_support.py`. **Changing `EMBEDDING_DIMENSIONS` or columns on an existing DB requires a manual migration; none exists.**

**Test isolation:** `tests/db_support.py` forces `DATABASE_URL` to `TEST_DATABASE_URL` (default `postgresql+psycopg2://localhost:5432/procedureassist_test`), refuses any name not ending in `_test`, and points Ollama at a dead port (`127.0.0.1:9`) so tests cannot reach a model.

---

## 8. External services and dependencies

**Python (`requirements.txt`, pinned):** beautifulsoup4 4.15.0, fastapi 0.141.1, httpx 0.28.1, pgvector 0.5.1, playwright 1.63.0, psycopg2-binary 2.9.13, python-dotenv 1.2.3, sqlalchemy 2.0.54, uvicorn[standard] 0.53.0. `pydantic` is imported by `schemas.py` and `extractor.py` but is not listed; it is installed transitively with FastAPI.
**Optional (`requirements-speech.txt`):** huggingface_hub 2.2.0, sentencepiece 0.2.2, soundfile 0.14.0, torch 2.14.1, torchaudio 2.11.0, transformers 5.20.2. Tests use stdlib `unittest` and FastAPI's `TestClient` (needs httpx, already present).
**JavaScript (`frontend/package.json`, pinned):** runtime `react` 19.3.0, `react-dom` 19.3.0; dev `vite` 8.3.1, `@vitejs/plugin-react` 6.1.1, `typescript` 7.0.2, `vitest` ~5.0.3, `jsdom` 30.1.2, `@testing-library/react` 16.3.3, `@testing-library/dom` 10.4.2, `@types/react(-dom)` 19.3.0. Root `package.json` has no dependencies. No lockfile is created (`run.sh` uses `--no-package-lock`), so installs are only as reproducible as the exact pins.

**Services and models (each backed by code):**
| Integration | Where | Detail |
|---|---|---|
| Ollama (LLM) | `extractor.call_qwen` | POST `/api/generate`, `format=json`, `think=false`, `temperature=0`; model `LLM_MODEL` (`qwen3:8b` default); 60 s timeout |
| Ollama (embeddings) | `rag.embed_texts` | POST `/api/embed`, model `EMBEDDING_MODEL` (`qwen3-embedding:0.6b`), 1024 dims, 60 s timeout |
| Ollama health | `routes.readiness`, `start.sh` | GET `/api/tags` |
| PostgreSQL + pgvector | `database.py`, `models.py` | `psycopg2`, `pgvector.sqlalchemy.Vector`, JSONB |
| Playwright Chromium | `scraper.fetch_rendered_html` | headless, fallback only; `run.sh` runs `playwright install chromium` |
| httpx + BeautifulSoup | `scraper` | static fetch and cleaning |
| Indic-Transcribe Flex | `speech._load`, `config.SPEECH_MODEL` | Hugging Face `bodhan-ai/indic-transcribe-flex`, local weights only (`local_files_only=True`); loads the model's own `indic_transcribe` Python module from the download directory and executes it in the backend process |
| Browser APIs | `VoiceInput`, `CitizenPage.ReadAloud` | `getUserMedia`, `MediaRecorder`, `OfflineAudioContext`, `speechSynthesis` |
| Homebrew | `start.sh` | `brew services start postgresql@16` |

No external SaaS or cloud API (OpenAI, etc.) is referenced in the code. The only outbound internet traffic from the backend is fetching the admin-submitted source URLs.

---

## 9. Tests and documentation overview

**Python tests (`tests/`, `unittest`):** `test_auth` (10), `test_config` (6), `test_end_to_end` (1), `test_extractor` (8), `test_guidance` (48), `test_health` (4), `test_identify` (41), `test_normalize` (11), `test_procedures` (7), `test_rag` (15), `test_routes` (10), `test_save` (7), `test_scraper` (29), `test_speech` (12) — counts are `def test` occurrences, not results. DB tests need a `*_test` Postgres DB and are skipped when unavailable unless `REQUIRE_DB_TESTS=1`. Commands per README: `REQUIRE_DB_TESTS=1 .venv/bin/python -m unittest discover -s tests`.
**Frontend tests:** `AdminPage.test.tsx`, `AdminProcedureList.test.tsx`, `App.test.tsx`, `CitizenPage.test.tsx`, `VoiceInput.test.tsx`, `api.test.ts` (Vitest, jsdom): `npm test --prefix frontend`; type check + build: `npm run build --prefix frontend` (`tsc --noEmit && vite build`).
**I did not run any tests.** Prior run outputs are in `PROCEDUREASSIST_HANDOFF/evidence/test_results/` and were not re-verified.
**Evaluation data/scripts:** `scripts/evaluate_*.py` with `fixtures/evaluation/*.json`; these need live Ollama and a DB and are read-only against the DB per their docstrings.
**Docs:** `README.md` (setup, run, Tamil/voice, tests, limitations), `DEMO.md` (demo runbook), `PROCEDUREASSIST_HANDOFF/00–12` (start-here, overview, architecture, AI/RAG, audit history, evaluation results, source URL audit, DB and safety, dev history, setup runbook, pending work, decision log, RAG reliability audit) and `evidence/`.
**Working tree state (git status at session start):** branch `arun-nm`; modified: `README.md`, `backend/{procedure_search,rag,routes,schemas,scraper}.py`, `frontend/src/{CitizenPage.test.tsx,CitizenPage.tsx,api.ts}`, `scripts/evaluate_{answers,needs}.py`, `tests/{db_support,test_guidance,test_identify,test_rag,test_scraper}.py`; untracked: `PROCEDUREASSIST_HANDOFF/`, `fixtures/evaluation/heldout.json`. This report describes the working tree including those uncommitted edits, not the last commit (`3491415 staging`).

---

## 10. Unclear areas requiring further investigation

1. **Live database contents and indexes.** No DB was queried. Whether a vector index exists, how many procedures are stored, and whether staging vs main databases exist (the evidence folder names `procedureassist_staging`) need `evidence/database/*` and `07_DATABASE_AND_SAFETY.md`.
2. **Chunks vs edited fields.** Admin edits to name/summary/steps are saved in `structured_data`, but retrieval and answers use chunks from the raw scraped `source_text`. Confirm that is intended (answers never reflect admin corrections).
3. **No "official source" gate.** `provenance_token` proves extraction, not that the domain is governmental. Whether any allow-list policy is meant to exist is not in code.
4. **Speech model.** The existence of the `indic_transcribe` module and its API (`IndicTranscribe.from_pretrained`, call signature `model(path, lang=, mode=)`) is assumed from the model card; it was not verifiable here. It executes third-party code inside the backend process.
5. **Hidden time limits.** `call_qwen` has a 60 s timeout, but `/api/guidance` makes up to two LLM calls (+ possibly more via `answer_from_naming_pages`), and the UI says "can take up to a minute". Behaviour on a cold or slow model is untested here.
6. **`create_all` on import** means importing `backend.main` touches the database; and `config` raising at import makes partial imports fail (there is an evidence note `single_module_import_note.txt` on this).
7. **Auth hardening.** No login rate limit, no server-side session revocation, and a single shared admin (acknowledged in README Limitations).
8. **Reproducibility.** No lock files; `run.sh` reinstalls Python deps and Chromium on every start; README says Python 3.14 and Node 22+, while the pinned versions (e.g. TypeScript 7.0.2, Vite 8.3.1) were not independently checked against a registry.
9. **Heuristic dependence.** Several behaviours are regex/word-list heuristics marked by the authors with `ponytail:` comments (`normalize.ROMANIZED_TAMIL`, `procedure_search.MULTI_HINT`, `procedure_search.mentions`, `rag.GENERIC_NAME_WORDS`). Their false-positive/negative rates are in the evaluation docs, not in code.
10. **Uncommitted work.** 16 modified files plus the untracked handoff folder and `heldout.json` mean the committed history does not equal what runs today; decide what to commit before anyone relies on git history.
