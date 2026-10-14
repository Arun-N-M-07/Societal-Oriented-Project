#!/usr/bin/env bash
# One command to start everything: Postgres, Ollama, backend, frontend.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

brew services start postgresql@16 >/dev/null 2>&1 || true

if ! curl -s localhost:11434/api/tags >/dev/null; then
    echo "Starting Ollama..."
    nohup ollama serve >/tmp/ollama.log 2>&1 &
    until curl -s localhost:11434/api/tags >/dev/null; do sleep 1; done
fi

echo "Warming up Qwen (first load is slow)..."
ollama run qwen3:8b "hi" >/dev/null 2>&1 || true

(sleep 6 && open http://localhost:5173) &
exec ./run.sh
