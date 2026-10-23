# ProcedureAssist

ProcedureAssist turns official government web pages into reviewed, step-by-step
procedures and helps citizens find them.

- **Admin** (`/admin`): sign in, paste an official URL, review what the local Qwen model
  extracted, and approve it. Approval saves the procedure and indexes the page text so it
  can be searched and quoted.
- **Citizen** (`/`): describe a situation in plain words, get the matching procedure (or
  choose between close matches), read its steps and official link, and ask follow-up
  questions. Every answer quotes the official page word for word; if the page doesn't
  answer the question, the app says so.

It gives guidance only and never submits applications.

## Stack

- Backend: Python 3.14, FastAPI, SQLAlchemy, PostgreSQL 16 with pgvector
- Scraping: httpx and BeautifulSoup, with Playwright (Chromium) for JavaScript pages
- Models (local, via Ollama): `qwen3:8b` for extraction and answers, `qwen3-embedding:0.6b` for search
- Frontend: React, TypeScript, Vite

## Setup (macOS)

1. Install Python 3.14, Node 22+, PostgreSQL 16 and pgvector (`brew install postgresql@16 pgvector`)
   and [Ollama](https://ollama.com).
2. Download the models:
   ```bash
   ollama pull qwen3:8b
   ollama pull qwen3-embedding:0.6b
   ```
3. Create the database and enable pgvector:
   ```bash
   brew services start postgresql@16
   createdb procedureassist
   psql -d procedureassist -c "CREATE EXTENSION vector"
   ```
4. Configure the environment:
   ```bash
   cp .env.example .env
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # paste as SECRET_KEY
   .venv/bin/python -m backend.auth                                 # paste as ADMIN_PASSWORD_HASH
   ```
   Set `DATABASE_URL` too. `.env.example` describes every setting; never commit `.env`.

## Running

```bash
./start.sh
```

This starts PostgreSQL and Ollama, checks both models are installed, then runs `run.sh`,
which installs dependencies and starts the backend (http://localhost:8000) and frontend
(http://localhost:5173). Open http://localhost:5173 (citizens) or
http://localhost:5173/admin. Use `localhost`, not `127.0.0.1`, because the backend only
accepts the origin set in `FRONTEND_ORIGIN`.

`GET /health/ready` reports whether the database and models are available.
Procedures saved before indexing existed can be indexed with
`.venv/bin/python -m backend.rag backfill` (safe to run again).

## Tamil and voice input (optional)

Citizens can choose English or Tamil and type or speak their question. Tamil, Romanized
Tamil and Tamil-English questions are rewritten by `qwen3:8b` (`backend/normalize.py`) into
one English search query; English questions skip this step. The existing search, answers
and citation checks then run on that query. The page shows what the citizen said and the
query that was searched ("Searched as"); a question that names no service gets a request
for clarification instead of a search. Answers stay in English.

Voice input transcribes on this machine with
[Indic-Transcribe Flex](https://huggingface.co/bodhan-ai/indic-transcribe-flex)
(1.2B parameters, 4.6 GB download, Indic Open Model License v1.0; credit the model, and
offering it as a service to others needs the licensor's approval). Without it, voice
input answers "not set up" and everything else works. To install:

1. On the model page, sign in, accept the licence conditions and request access.
2. Install the packages and log in once (stores a token in `~/.cache/huggingface`):

   ```bash
   .venv/bin/pip install -r requirements-speech.txt
   .venv/bin/hf auth login
   .venv/bin/python -c 'from huggingface_hub import snapshot_download; print(snapshot_download("bodhan-ai/indic-transcribe-flex"))'
   ```

3. Restart the backend. The model loads on the first recording (allow a minute) and is
   reused afterwards; recordings are transcribed one at a time. `SPEECH_MODEL_DIR` can point
   at a copy of the model folder instead of the Hugging Face cache.

The model's own Python code (in the download) runs inside the backend, as its model card
requires. The browser converts each recording (up to 30 s) to 16 kHz mono WAV and sends it to
`POST /api/speech/transcribe?language=ta|en`; the server checks it is real WAV audio, writes
it to a temporary file only for the model, deletes it afterwards and returns the text. Audio
and transcripts are not stored or logged by ProcedureAssist. The transcript is placed in the
question box for the citizen to correct; nothing is sent until they press Send.
"Read aloud" uses only voices installed on the device.

`.venv/bin/python scripts/evaluate_needs.py fixtures/evaluation/tamil.json` runs 36 labelled
questions in 12 categories (uses Ollama, writes nothing).

## Tests

Database tests run against a separate database whose name must end in `_test`, never
against `procedureassist`.

```bash
createdb procedureassist_test                      # once
REQUIRE_DB_TESTS=1 .venv/bin/python -m unittest discover -s tests
npm test --prefix frontend
npm run build --prefix frontend                    # type check and production build
```

Without `REQUIRE_DB_TESTS=1`, database tests are skipped when the test database is
unavailable. Tests never call Ollama.

`.venv/bin/python scripts/evaluate_identification.py` re-checks the search thresholds
against real official pages (uses Ollama, writes nothing).
`.venv/bin/python scripts/evaluate_needs.py` compares single- and multi-need handling on the
labelled messages in `fixtures/evaluation/multi_need.json` (uses Ollama and the saved
procedures, writes nothing).
`.venv/bin/python scripts/evaluate_answers.py` asks the 80 questions in
`fixtures/evaluation/answers.json` through the real API, checks each answer's quotes and
citations, and names the stage where each failure happened (uses Ollama, writes nothing).

## Troubleshooting

| Problem | Fix |
|---|---|
| Backend exits with "... must be set" | Add the setting to `.env` |
| `type "vector" does not exist` | `psql -d procedureassist -c "CREATE EXTENSION vector"` |
| Network or CORS errors in the browser | Use `http://localhost:5173`, not `127.0.0.1` |
| Extract returns 502 | Ollama is down or a model is missing; check `/health/ready` |
| Extract returns 422 | The site blocked the request or the page has no readable text |
| Save returns 409 | That URL is already saved; delete it from the admin list first |

## Limitations

- Only HTML pages work; PDFs and login- or bot-protected sites are not supported.
- Hosts are checked before every request, but DNS rebinding is not fully prevented.
- Answers are checked for a word-for-word quote with the same numbers and negation, not
  for every possible change in meaning.
- Search thresholds come from a small labelled set (32 questions over 10 pages). The app
  asks the citizen to choose only when the top matches score within 0.03 of each other.
- Admin sessions are signed cookies that last 12 hours; logging out does not revoke a
  copied cookie, and login attempts are not rate limited. Changing `SECRET_KEY` signs
  everyone out.
- Deleting a procedure is permanent.
- Tamil support is tested on 36 questions written for this project (also used to tune the
  prompt), not on real citizens' speech or Chennai slang in general. The 8B model sometimes
  changes the question type or drops a detail; the citizen sees the searched query.
- Voice input was tested with the real model only on synthetic macOS voices (Aman,
  Rishi, Vani), not on real citizens' speech. It runs on the CPU (the model's code uses only
  CUDA or CPU): about 6 s to load, about 2 s per 2–3 s clip, about 5.4 GB of memory.
  Tamil-accented English words can be misheard (for example "EPF" as "EBIL"), so citizens
  should check the transcript before sending. Answers are not translated into Tamil.
