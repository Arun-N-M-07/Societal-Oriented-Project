import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set in the environment or .env file")
    return value


def _setting(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


DATABASE_URL = _required_setting("DATABASE_URL")
OLLAMA_BASE_URL = _setting("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = _setting("LLM_MODEL", "qwen3:8b")
# Context window requested from Ollama; must fit the longest allowed source text.
LLM_CONTEXT_TOKENS = int(_setting("LLM_CONTEXT_TOKENS", "32768"))
EMBEDDING_MODEL = _setting("EMBEDDING_MODEL", "qwen3-embedding:0.6b")
# Must match the embedding model (qwen3-embedding:0.6b returns 1024 values).
EMBEDDING_DIMENSIONS = int(_setting("EMBEDDING_DIMENSIONS", "1024"))
FRONTEND_ORIGIN = _setting("FRONTEND_ORIGIN", "http://localhost:5173")
SECRET_KEY = _required_setting("SECRET_KEY")
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be at least 32 characters long")
ADMIN_USERNAME = _setting("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = _required_setting("ADMIN_PASSWORD_HASH")
if not ADMIN_PASSWORD_HASH.startswith("scrypt$"):
    raise RuntimeError("ADMIN_PASSWORD_HASH must come from: python -m backend.auth")
COOKIE_SECURE = _setting("COOKIE_SECURE", "false").lower() == "true"
# Procedure identification thresholds (cosine similarity, chosen from
# scripts/evaluate_identification.py on the labelled evaluation set).
IDENTIFY_MIN_SCORE = float(_setting("IDENTIFY_MIN_SCORE", "0.53"))
IDENTIFY_MARGIN = float(_setting("IDENTIFY_MARGIN", "0.03"))
# Needs answered per message; the rest are listed for the citizen to send next.
MAX_NEEDS = int(_setting("MAX_NEEDS", "3"))
