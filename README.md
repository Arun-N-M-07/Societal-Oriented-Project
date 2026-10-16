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
