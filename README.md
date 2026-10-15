# ProcedureAssist

ProcedureAssist turns official government web pages into human-reviewed procedures
and helps citizens find and understand them.

- **Admin** (`/admin`): sign in, extract a procedure from an official URL (scraper +
  local Qwen model), review and edit it, approve it. Approval stores the procedure and
  indexes its official text as evidence.
- **Citizen** (`/`): describe a situation in plain language, get the matching approved
  procedure (or choose between plausible ones), read its steps and official link, and
  ask follow-up questions. Answers contain only claims backed by a verbatim quote from
  the official text; otherwise the app says it cannot answer.

ProcedureAssist gives guidance only. It never submits applications.

## Stack

FastAPI, SQLAlchemy, PostgreSQL 16 with pgvector, Ollama (`qwen3:8b` for extraction
and answers, `qwen3-embedding:0.6b` for search), Playwright for JavaScript pages,
React + TypeScript + Vite.

## Setup (macOS)

1. Install Python 3.14, Node 22+, PostgreSQL 16 (`brew install postgresql@16`),
   pgvector (`brew install pgvector`) and [Ollama](https://ollama.com).
2. Download the models:
   ```bash
   ollama pull qwen3:8b
   ollama pull qwen3-embedding:0.6b
   ```
3. Create the database and enable pgvector once:
   ```bash
   brew services start postgresql@16
   createdb procedureassist
   psql -d procedureassist -c "CREATE EXTENSION vector"
   ```
4. Create `.env` from the example and fill it in:
   ```bash
   cp .env.example .env
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   .venv/bin/python -m backend.auth                                 # ADMIN_PASSWORD_HASH
   ```
   `.env` must never be committed. `.env.example` lists every setting.
5. Start everything:
   ```bash
   ./start.sh
   ```
   It starts PostgreSQL and Ollama, checks both models are installed, then runs
   `run.sh` (installs dependencies, checks the database, starts the backend on
   http://localhost:8000 and the frontend on http://localhost:5173).

Open http://localhost:5173 for citizens and http://localhost:5173/admin for admins.
Use `localhost`, not `127.0.0.1`: the backend only accepts the origin in `FRONTEND_ORIGIN`.

Procedures saved before evidence indexing existed can be indexed once with
`.venv/bin/python -m backend.rag backfill` (safe to re-run).

## Tests

Database tests use a separate database whose name must end in `_test`; they never touch
`procedureassist`.

```bash
createdb procedureassist_test                     # once; tests enable pgvector in it
REQUIRE_DB_TESTS=1 .venv/bin/python -m unittest discover -s tests
npm test --prefix frontend
npm run build --prefix frontend                   # type check + production build
```

Without `REQUIRE_DB_TESTS=1`, database tests are skipped (with a reason) when the test
database is unreachable. Set `TEST_DATABASE_URL` to use a different test database. Unit
tests never call Ollama.

To re-check identification thresholds against real official pages (uses Ollama, writes
nothing): `.venv/bin/python scripts/evaluate_identification.py`.

## API

| Endpoint | Access | Purpose |
|---|---|---|
| `GET /health`, `GET /health/ready` | public | Liveness; readiness of database, pgvector table and Ollama models (503 if not ready) |
| `POST /api/admin/login`, `POST /api/admin/logout`, `GET /api/admin/session` | public / admin | Admin session (HttpOnly, SameSite=Strict cookie) |
| `POST /api/admin/extract` | admin | Scrape a URL and extract a procedure; returns a signed provenance token |
| `POST /api/admin/re-extract` | admin | Re-run extraction on the same verified text |
| `POST /api/admin/procedures` | admin | Approve: verify provenance, save and index the procedure |
| `GET /api/admin/procedures`, `DELETE /api/admin/procedures/{id}` | admin | List; permanently delete a procedure and its evidence |
| `GET /api/procedures`, `GET /api/procedures/{id}` | public, read-only | Approved procedures (never the source text) |
| `POST /api/identify` | public, read-only | `matched`, `ambiguous` (2-3 candidates) or `no_match` |
| `POST /api/guidance` | public, read-only | Quote-verified answer for one procedure, or `insufficient_evidence` |

## Troubleshooting

| Problem | Fix |
|---|---|
| Backend exits with "... must be set" | Add the setting to `.env` (see `.env.example`) |
| `type "vector" does not exist` at startup | Run `psql -d procedureassist -c "CREATE EXTENSION vector"` |
| Browser shows network/CORS errors | Open `http://localhost:5173`, not `127.0.0.1` |
| Extract returns 502 | Ollama is not running or a model is missing (`ollama list`); check `/health/ready` |
| Extract returns 422 for a real site | The site blocked or failed the request, or the page has no readable text |
| Save returns 409 | That URL is already saved; delete it in the admin list first |
| `Port ... already in use` | Stop the previous `run.sh` with Ctrl+C |

## Known limitations

- Only HTML pages are supported (no PDFs, login-protected or bot-protected sites).
- Hostnames are resolved and checked before every request, but a host that changes its
  DNS answer between the check and the connection (DNS rebinding) is not fully prevented.
- Provenance tokens prove the server extracted the saved text; they do not prove a site
  is an authoritative government source.
- Answer verification proves each claim has a verbatim supporting quote; it does not
  prove the paraphrase means exactly what the quote says.
- Identification thresholds were chosen on a small labelled set (32 questions,
  10 pages); re-run the evaluation as procedures are added.
- Deleting a procedure is permanent; there is no audit history of withdrawn procedures.
