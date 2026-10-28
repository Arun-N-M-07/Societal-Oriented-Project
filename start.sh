#!/usr/bin/env bash
# One command to start everything: PostgreSQL, Ollama, backend and frontend.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# Read a value from .env without sourcing it (values may contain "$").
setting() {
    local value
    value=$(grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2-)
    echo "${value:-$2}"
}
OLLAMA_URL=$(setting OLLAMA_BASE_URL http://localhost:11434)
LLM_MODEL=$(setting LLM_MODEL qwen3:8b)
EMBEDDING_MODEL=$(setting EMBEDDING_MODEL qwen3-embedding:0.6b)

# First free port at or above the given one, so a leftover server never blocks start-up.
free_port() {
    local port=$1
    while lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; do port=$((port + 1)); done
    echo "$port"
}
export BACKEND_PORT=$(free_port 8000)
export FRONTEND_PORT=$(free_port 5173)
export FRONTEND_ORIGIN="http://localhost:$FRONTEND_PORT"
export VITE_API_BASE_URL="http://localhost:$BACKEND_PORT"

brew services start postgresql@16 >/dev/null 2>&1 || true

if ! curl -s "$OLLAMA_URL/api/tags" >/dev/null; then
    echo "Starting Ollama..."
    nohup ollama serve >/tmp/ollama.log 2>&1 &
    until curl -s "$OLLAMA_URL/api/tags" >/dev/null; do sleep 1; done
fi

for model in "$LLM_MODEL" "$EMBEDDING_MODEL"; do
    if ! curl -s "$OLLAMA_URL/api/tags" | grep -q "\"name\":\"$model\""; then
        echo "Missing Ollama model $model. Run: ollama pull $model"
        exit 1
    fi
done

echo "Warming up $LLM_MODEL (first load is slow)..."
ollama run "$LLM_MODEL" "hi" >/dev/null 2>&1 || true

(sleep 6 && open http://localhost:$FRONTEND_PORT) &
exec ./run.sh
