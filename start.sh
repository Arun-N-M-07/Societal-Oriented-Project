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

(sleep 6 && open http://localhost:5173) &
exec ./run.sh
