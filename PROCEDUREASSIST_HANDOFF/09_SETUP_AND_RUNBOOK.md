# 09 — Setup and runbook (macOS)

Settings live in `.env`, which is never committed. `.env.example` lists every key:
- `DATABASE_URL`, `OLLAMA_BASE_URL`, `LLM_MODEL`, `LLM_CONTEXT_TOKENS`;
- `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `FRONTEND_ORIGIN`;
- `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, `COOKIE_SECURE`.

Never put real values in documentation or logs.

## First-time setup
1. **Install the prerequisites.** You need Python 3.14, Node 22+, PostgreSQL 16 and pgvector, and Ollama:
   ```bash
   brew install postgresql@16 pgvector
   ```
2. **Pull the models:**
   ```bash
   ollama pull qwen3:8b
   ollama pull qwen3-embedding:0.6b
   ```
3. **Create the database:**
   ```bash
   brew services start postgresql@16
   createdb procedureassist
   psql -d procedureassist -c "CREATE EXTENSION vector"
   ```
4. **Create `.env`:**
   ```bash
   cp .env.example .env
   ```
5. **Create the virtual environment and install packages:**
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```
6. **Generate a random `SECRET_KEY`** and paste it into `.env`:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
7. **Create `ADMIN_PASSWORD_HASH`.** This prompts for a password and prints the hash to paste into `.env`:
   ```bash
   .venv/bin/python -m backend.auth
   ```
8. **Set `DATABASE_URL` in `.env`.**
9. **Optional: speech.** Follow README "Tamil and voice input". It needs a Hugging Face login and the model licence accepted.

## Running
```bash
./start.sh
```
This starts PostgreSQL and Ollama, checks both models, then runs `run.sh`: the backend on http://localhost:8000 and the frontend on http://localhost:5173.
- **Citizen page:** http://localhost:5173
- **Admin page:** http://localhost:5173/admin
- Use `localhost`, not `127.0.0.1`, because CORS allows only `FRONTEND_ORIGIN`.
- **Readiness:** http://localhost:8000/health/ready must show `"status":"ok"`.

## Adding or replacing a source (the only approved way)
1. Admin page → paste the official URL → **Extract**. This scrapes the page and drafts the procedure with the model. Nothing is saved yet.
2. Read the scraped text. Check that the fees, conditions and steps match the official page. Correct the name, department and steps.
3. **Approve and save.** This chunks and embeds the text and saves it in one transaction.
4. To replace an existing URL, delete the old record first (the URL is unique), then approve the new one. Take a backup first (see `07_DATABASE_AND_SAFETY.md`).

For many pages at once there is a batch script. It asks for the admin password and asks y/n per page:
```bash
.venv/bin/python scripts/approve_batch.py fixtures/ingestion/demo_batch.json
```

## Tests
**Backend.** Database tests need a separate database whose name ends in `_test`. Create it once:
```bash
createdb procedureassist_test
```
Then run the suite:
```bash
REQUIRE_DB_TESTS=1 .venv/bin/python -m unittest discover -s tests
```
- **One file:** use `-p test_rag.py`.
- `python -m unittest tests.test_rag` fails with "No module named db_support". The test files import `db_support` as a top-level module, so `discover -s tests` must be used. This predates the 23 Oct work and is not a test failure.

**Frontend:**
```bash
npm test --prefix frontend
```

**TypeScript and production build:**
```bash
npm run build --prefix frontend
```

**Unused-code check:**
```bash
cd frontend && npx tsc --noEmit --noUnusedLocals --noUnusedParameters
```

## Evaluations (real models; read-only)

The 80-question answer evaluation:
```bash
.venv/bin/python scripts/evaluate_answers.py
```

The 27 held-out questions:
```bash
.venv/bin/python scripts/evaluate_answers.py fixtures/evaluation/heldout.json
```

Single- and multi-need identification:
```bash
.venv/bin/python scripts/evaluate_needs.py fixtures/evaluation/multi_need.json
```
The same script takes `population.json`, `demo_services.json` and `tamil.json`.

Search thresholds:
```bash
.venv/bin/python scripts/evaluate_identification.py
```

Notes on running evaluations:
- **Using the staging copy.** Prefix any command with `DATABASE_URL=<same URL but database procedureassist_staging>`. The environment variable wins over `.env`, and `.env` is not edited.
- **Run evaluations one at a time.** They share one Ollama instance.
- **Waiting for a run.** Never wait with `until ! pgrep -f "evaluate_answers.py"` started from a shell whose own command line contains that text: it matches itself and never ends. Wait on the process ID or chain the commands instead.
- **Run time.** About 15–20 min per 80-question run on an Apple-silicon laptop.

## Troubleshooting
| Problem | Fix |
|---|---|
| Backend exits with "... must be set" | Add the setting to `.env`. |
| `type "vector" does not exist` | Run `psql -d procedureassist -c "CREATE EXTENSION vector"`. |
| CORS errors in the browser | Use http://localhost:5173. |
| Extract returns 502 | Ollama is down or a model is missing; check `/health/ready`. |
| Extract returns 422 | The site blocked the request, or the page has no readable text (PDFs are not supported). |
| Save returns 409 | The URL already exists. Delete it first (after a backup). |
