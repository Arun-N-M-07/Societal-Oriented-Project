import getpass
import hashlib
import hmac
import os
import time

from fastapi import Cookie, HTTPException


PROVENANCE_TTL_SECONDS = 2 * 60 * 60
SESSION_TTL_SECONDS = 12 * 60 * 60
SESSION_COOKIE = "admin_session"
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


class ProvenanceError(Exception):
    pass


# Settings are imported inside functions so that `python -m backend.auth`
# can hash a password before the required settings exist.
def sign(payload: str) -> str:
    from backend.config import SECRET_KEY

    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        name, n, r, p, salt, digest = stored_hash.split("$")
        expected = bytes.fromhex(digest)
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
            dklen=len(expected),
        )
    except ValueError:
        return False
    return name == "scrypt" and hmac.compare_digest(actual, expected)


def check_admin_credentials(username: str, password: str) -> bool:
    from backend.config import ADMIN_PASSWORD_HASH, ADMIN_USERNAME

    password_ok = verify_password(password, ADMIN_PASSWORD_HASH)
    return hmac.compare_digest(username, ADMIN_USERNAME) and password_ok


def create_session_token(username: str) -> str:
    payload = f"session:{int(time.time()) + SESSION_TTL_SECONDS}:{username}"
    return f"{payload}:{sign(payload)}"


def require_admin(admin_session: str | None = Cookie(default=None)) -> str:
    """FastAPI dependency: return the admin username or reject with 401."""
    from backend.config import ADMIN_USERNAME

    payload, _, signature = (admin_session or "").rpartition(":")
    parts = payload.split(":", 2)
    if (
        len(parts) == 3
        and parts[0] == "session"
        and hmac.compare_digest(sign(payload), signature)
        and int(parts[1]) > time.time()
        and parts[2] == ADMIN_USERNAME
    ):
        return parts[2]
    raise HTTPException(status_code=401, detail="Admin authentication required.")


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


if __name__ == "__main__":
    password = getpass.getpass("New admin password: ")
    if len(password) < 12 or password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords must match and be at least 12 characters.")
    print(hash_password(password))
