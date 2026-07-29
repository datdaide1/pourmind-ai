import pytest
from fastapi import HTTPException

from app.core.session_auth import create_session_token, require_session_token


def test_session_token_is_bound_to_session_id():
    first = create_session_token("session-a")
    second = create_session_token("session-b")

    assert first != second
    require_session_token("session-a", first)


@pytest.mark.parametrize(
    ("token", "status_code"),
    [(None, 401), ("wrong-token", 403)],
)
def test_session_token_rejects_missing_or_invalid_credentials(token, status_code):
    with pytest.raises(HTTPException) as exc_info:
        require_session_token("session-a", token)

    assert exc_info.value.status_code == status_code


def test_session_token_cannot_be_reused_for_another_session():
    token = create_session_token("session-a")

    with pytest.raises(HTTPException) as exc_info:
        require_session_token("session-b", token)

    assert exc_info.value.status_code == 403
