import hashlib
import hmac
import logging
import secrets

from fastapi import HTTPException

from app.core.config import settings


logger = logging.getLogger(__name__)

_ephemeral_secret = secrets.token_urlsafe(48)
if not settings.SESSION_TOKEN_SECRET:
    logger.warning(
        "SESSION_TOKEN_SECRET is not configured; session tokens will be invalidated "
        "when this process restarts. Configure a stable secret in production."
    )


def _secret() -> bytes:
    return (settings.SESSION_TOKEN_SECRET or _ephemeral_secret).encode("utf-8")


def create_session_token(session_id: str) -> str:
    return hmac.new(_secret(), session_id.encode("utf-8"), hashlib.sha256).hexdigest()


def require_session_token(session_id: str, supplied_token: str | None) -> None:
    if not supplied_token:
        raise HTTPException(status_code=401, detail="Missing session token")

    expected_token = create_session_token(session_id)
    if not hmac.compare_digest(expected_token, supplied_token):
        raise HTTPException(status_code=403, detail="Invalid session token")
