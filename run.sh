#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

command -v python3 >/dev/null || {
    echo "Python 3 is required."
    exit 1
}
command -v npm >/dev/null || {
    echo "Node.js and npm are required."
    exit 1
}

if [[ ! -f .env ]]; then
    echo "Missing .env file. Run: cp .env.example .env"
    echo "Then update DATABASE_URL and run this script again."
    exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt
.venv/bin/playwright install chromium
if [[ ! -d frontend/node_modules ]]; then
    npm install --prefix frontend --no-audit --no-fund --package-lock=false
fi

if ! .venv/bin/python -c \
    'from backend.database import engine; connection = engine.connect(); connection.close()'; then
    echo "PostgreSQL is unavailable. Start it and check DATABASE_URL in .env."
    exit 1
fi

backend_pid=""
frontend_pid=""

cleanup() {
    trap - EXIT HUP INT TERM
    [[ -n "$backend_pid" ]] && kill "$backend_pid" 2>/dev/null || true
    [[ -n "$frontend_pid" ]] && kill "$frontend_pid" 2>/dev/null || true
    [[ -n "$backend_pid" ]] && wait "$backend_pid" 2>/dev/null || true
    [[ -n "$frontend_pid" ]] && wait "$frontend_pid" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
backend_pid=$!
(
    cd frontend
    exec ./node_modules/.bin/vite --host 127.0.0.1 --port 5173 --strictPort
) &
frontend_pid=$!

echo "Backend: http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:5173"
echo "Press Ctrl+C to stop both servers."

while kill -0 "$backend_pid" 2>/dev/null \
    && kill -0 "$frontend_pid" 2>/dev/null; do
    sleep 1
done

if ! kill -0 "$backend_pid" 2>/dev/null; then
    wait "$backend_pid"
else
    wait "$frontend_pid"
fi
