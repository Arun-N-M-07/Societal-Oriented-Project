import hashlib
import hmac
import time

from backend.config import SECRET_KEY


PROVENANCE_TTL_SECONDS = 2 * 60 * 60


class ProvenanceError(Exception):
    pass


def sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _source_digest(source_url: str, source_text: str) -> str:
    return hashlib.sha256(f"{source_url}\n{source_text}".encode()).hexdigest()


def issue_provenance_token(source_url: str, source_text: str) -> str:
    expires_at = int(time.time()) + PROVENANCE_TTL_SECONDS
    payload = f"provenance:{expires_at}:{_source_digest(source_url, source_text)}"
    return f"{payload}:{sign(payload)}"


def verify_provenance_token(token: str, source_url: str, source_text: str) -> None:
    """Prove this server recently extracted exactly this text from this URL.

    This says nothing about whether the URL is an authoritative government
    source; that is a separate check.
    """
    payload, _, signature = token.rpartition(":")
    parts = payload.split(":")
    if (
        len(parts) != 3
        or parts[0] != "provenance"
        or not hmac.compare_digest(sign(payload), signature)
        or not hmac.compare_digest(parts[2], _source_digest(source_url, source_text))
    ):
        raise ProvenanceError(
            "The source does not match the extracted page. Extract it again."
        )
    if int(parts[1]) < time.time():
        raise ProvenanceError("This extraction has expired. Extract it again.")
