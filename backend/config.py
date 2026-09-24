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
EMBEDDING_MODEL = _setting("EMBEDDING_MODEL", "qwen3-embedding:0.6b")
FRONTEND_ORIGIN = _setting("FRONTEND_ORIGIN", "http://localhost:5173")
