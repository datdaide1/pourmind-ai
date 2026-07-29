import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from app.agents.nodes import deterministic_safety_check, router_node
from app.api.endpoints import ChatMessagePayload
from app.core.config import settings
from app.core.request_controls import ChatRequestControls
from app.tools.qdrant_retriever import search_qdrant


def test_deterministic_safety_precheck_blocks_hazchem_and_underage():
    assert deterministic_safety_check("mix bleach with ammonia")[0] == "hazchem_blocked"
    assert deterministic_safety_check("I am 16 and want a gin cocktail") == ("underage_redirect", 16)

    assert deterministic_safety_check("tr\u1ed9n h\u00f3a ch\u1ea5t \u0111\u1ed9c")[0] == "hazchem_blocked"
    assert deterministic_safety_check("T\u00f4i 16 tu\u1ed5i v\u00e0 mu\u1ed1n u\u1ed1ng r\u01b0\u1ee3u") == ("underage_redirect", 16)

@pytest.mark.asyncio
async def test_router_fails_closed_when_classifier_is_unavailable():
    structured = AsyncMock()
    structured.ainvoke.side_effect = RuntimeError("provider detail must not escape")
    failing_llm = MagicMock()
    failing_llm.with_structured_output.return_value = structured
    with patch("app.agents.nodes.llm", failing_llm):
        result = await router_node({"messages": [HumanMessage(content="suggest something sweet")]})
    assert result["safety_status"] == "classifier_unavailable"


def test_chat_message_has_size_bound():
    with pytest.raises(ValidationError):
        ChatMessagePayload(session_id="s", content="x" * (settings.MAX_CHAT_MESSAGE_CHARS + 1))


@pytest.mark.asyncio
async def test_qdrant_limit_is_bounded_before_external_calls():
    with pytest.raises(ValueError, match="limit must be between"):
        await search_qdrant("query", "cocktails", settings.SEARCH_MAX_LIMIT + 1)


@pytest.mark.asyncio
async def test_chat_rate_and_concurrency_controls(monkeypatch):
    controls = ChatRequestControls()
    monkeypatch.setattr(settings, "CHAT_MAX_CONCURRENCY", 1)
    monkeypatch.setattr(settings, "CHAT_RATE_LIMIT_REQUESTS", 2)
    first = controls.acquire("session")
    await first.__aenter__()
    try:
        with pytest.raises(HTTPException) as concurrent:
            async with controls.acquire("session"):
                pass
        assert concurrent.value.status_code == 429
    finally:
        await first.__aexit__(None, None, None)


def test_cors_defaults_are_allowlisted():
    assert "*" not in settings.cors_allowed_origins_list
    assert settings.cors_allowed_origins_list
