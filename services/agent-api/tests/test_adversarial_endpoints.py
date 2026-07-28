import pytest
import uuid
import json
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.db.postgres import AsyncSessionLocal
from app.db.models import Conversation, Message, User
from langchain_core.messages import HumanMessage, AIMessage

# Determine the correct transport configuration for httpx version compatibility
try:
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
except ImportError:
    transport = None

def get_client():
    if transport is not None:
        return AsyncClient(transport=transport, base_url="http://test")
    else:
        return AsyncClient(app=app, base_url="http://test")

@pytest.fixture(autouse=True)
def mock_external_calls():
    # Mock get_relevant_venues and get_relevant_cocktails to prevent external DB/network requests
    with patch("app.api.endpoints.get_relevant_venues", new_callable=AsyncMock) as mock_venues, \
         patch("app.api.endpoints.get_relevant_cocktails", new_callable=AsyncMock) as mock_cocktails:
        mock_venues.return_value = [{"name": "Mock Venue", "address": "123 Street", "rating": 4.5}]
        mock_cocktails.return_value = [{"name": "Mock Cocktail", "alcoholic_type": "Alcoholic"}]
        yield

# ==========================================
# /session/init ENDPOINT ADVERSARIAL TESTS
# ==========================================

@pytest.mark.asyncio
async def test_session_init_invalid_uuid_format():
    """Verify that an invalid UUID format in user_id is handled gracefully and parsed to None (returns 200)."""
    session_id = f"test-adv-{uuid.uuid4()}"
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/init",
            json={
                "guest_session_id": session_id,
                "user_id": "not-a-uuid-string",
                "mode": "guest"
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    
    # Verify created in DB with user_id = None
    async with AsyncSessionLocal() as session:
        conv = (await session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )).scalar_one_or_none()
        assert conv is not None
        assert conv.user_id is None

@pytest.mark.asyncio
async def test_session_init_non_existent_uuid():
    """Verify that a valid UUID format but non-existent user_id returns HTTP 400."""
    session_id = f"test-adv-{uuid.uuid4()}"
    non_existent_user_id = str(uuid.uuid4())
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/init",
            json={
                "guest_session_id": session_id,
                "user_id": non_existent_user_id,
                "mode": "guest"
            }
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "User does not exist"

@pytest.mark.asyncio
async def test_session_init_missing_session_id():
    """Verify that missing guest_session_id causes a 422 validation error."""
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/init",
            json={
                "mode": "guest"
            }
        )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_session_init_empty_session_id():
    """Verify that an empty string for guest_session_id is accepted by Pydantic but inserted into DB."""
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/init",
            json={
                "guest_session_id": "",
                "mode": "guest"
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == ""

@pytest.mark.asyncio
async def test_session_init_extreme_session_id():
    """Verify that an extremely long guest_session_id (longer than VARCHAR(255)) returns HTTP 400."""
    long_session_id = "a" * 300
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/init",
            json={
                "guest_session_id": long_session_id,
                "mode": "guest"
            }
        )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_session_init_invalid_method():
    """Verify that GET on /session/init returns 405 Method Not Allowed."""
    async with get_client() as client:
        response = await client.get("/api/v1/session/init")
    assert response.status_code == 405


# ==========================================
# /chat/message ENDPOINT ADVERSARIAL TESTS
# ==========================================

@pytest.mark.asyncio
async def test_chat_message_missing_session_id():
    """Verify that missing session_id in /chat/message payload causes 422."""
    async with get_client() as client:
        response = await client.post(
            "/api/v1/chat/message",
            json={
                "content": "Hello"
            }
        )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_chat_message_empty_content():
    """Verify that empty content in chat message is processed but might yield a default or error message."""
    session_id = f"test-chat-adv-{uuid.uuid4()}"
    
    mock_events = [
        {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="I'm sorry, I could not generate a response.")}},
        {
            "event": "on_chain_end",
            "parent_ids": [],
            "data": {
                "output": {
                    "intent": "b2c",
                    "messages": [
                        HumanMessage(content=""),
                        AIMessage(content="I'm sorry, I could not generate a response.")
                    ]
                }
            }
        }
    ]
    
    async def mock_generator(*args, **kwargs):
        for ev in mock_events:
            yield ev
            
    with patch("app.api.endpoints.graph.astream_events", side_effect=mock_generator):
        async with get_client() as client:
            response = await client.post(
                "/api/v1/chat/message",
                json={
                    "session_id": session_id,
                    "content": ""
                }
            )
        assert response.status_code == 200
        assert "I'm sorry" in response.text

@pytest.mark.asyncio
async def test_chat_message_extreme_content():
    """Verify that extremely long content in chat message is parsed and handles database insertion."""
    session_id = f"test-chat-adv-{uuid.uuid4()}"
    long_content = "Please recommend " + ("a" * 10000)
    
    mock_events = [
        {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Here is a cocktail recommendation.")}},
        {
            "event": "on_chain_end",
            "parent_ids": [],
            "data": {
                "output": {
                    "intent": "b2c",
                    "messages": [
                        HumanMessage(content=long_content),
                        AIMessage(content="Here is a cocktail recommendation.")
                    ]
                }
            }
        }
    ]
    
    async def mock_generator(*args, **kwargs):
        for ev in mock_events:
            yield ev
            
    with patch("app.api.endpoints.graph.astream_events", side_effect=mock_generator):
        async with get_client() as client:
            response = await client.post(
                "/api/v1/chat/message",
                json={
                    "session_id": session_id,
                    "content": long_content
                }
            )
        assert response.status_code == 200
        assert "Here is a cocktail" in response.text

@pytest.mark.asyncio
async def test_chat_message_invalid_method():
    """Verify that GET on /chat/message returns 405 Method Not Allowed."""
    async with get_client() as client:
        response = await client.get("/api/v1/chat/message")
    assert response.status_code == 405


# ==========================================
# /tools/calculate_cost ENDPOINT ADVERSARIAL TESTS
# ==========================================

@pytest.mark.asyncio
async def test_calculate_cost_empty_recipe():
    """Verify that calculating cost for an empty recipe list returns zeros and does not divide by zero."""
    async with get_client() as client:
        response = await client.post(
            "/api/v1/tools/calculate_cost",
            json={
                "recipe": []
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total_cost_vnd"] == 0.0
    assert data["total_volume_ml"] == 0.0
    assert data["estimated_abv"] == 0.0

@pytest.mark.asyncio
async def test_calculate_cost_negative_amount():
    """Verify that negative amounts in recipe return HTTP 400."""
    async with get_client() as client:
        response = await client.post(
            "/api/v1/tools/calculate_cost",
            json={
                "recipe": [
                    {"ingredient": "Vodka", "amount_ml": -50.0}
                ]
            }
        )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_calculate_cost_non_existent_ingredient():
    """Verify that non-existent ingredients are defaulted to 0 cost and 0 ABV without throwing errors."""
    async with get_client() as client:
        response = await client.post(
            "/api/v1/tools/calculate_cost",
            json={
                "recipe": [
                    {"ingredient": "NonExistentIngredientXYZ", "amount_ml": 50.0}
                ]
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total_cost_vnd"] == 0.0
    assert data["total_volume_ml"] == 50.0
    assert data["estimated_abv"] == 0.0

@pytest.mark.asyncio
async def test_calculate_cost_extremely_large_amount():
    """Verify that extremely large volume values are parsed and don't cause overflow crashes in python."""
    async with get_client() as client:
        response = await client.post(
            "/api/v1/tools/calculate_cost",
            json={
                "recipe": [
                    {"ingredient": "Vodka", "amount_ml": 1e12}
                ]
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total_volume_ml"] == 1e12

@pytest.mark.asyncio
async def test_calculate_cost_invalid_method():
    """Verify that GET on /tools/calculate_cost returns 405 Method Not Allowed."""
    async with get_client() as client:
        response = await client.get("/api/v1/tools/calculate_cost")
    assert response.status_code == 405


# ==========================================
# /chat/history ENDPOINT ADVERSARIAL TESTS
# ==========================================

@pytest.mark.asyncio
async def test_chat_history_invalid_uuid():
    """Verify that invalid UUID string in user_id query parameter returns empty list gracefully instead of raising error."""
    async with get_client() as client:
        response = await client.get("/api/v1/chat/history?user_id=invalid-uuid-string")
    assert response.status_code == 200
    data = response.json()
    assert data["conversations"] == []

@pytest.mark.asyncio
async def test_chat_history_missing_user_id():
    """Verify that missing user_id query parameter causes a 422 error."""
    async with get_client() as client:
        response = await client.get("/api/v1/chat/history")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_chat_history_invalid_method():
    """Verify that POST on /chat/history returns 405 Method Not Allowed."""
    async with get_client() as client:
        response = await client.post("/api/v1/chat/history?user_id=some-id")
    assert response.status_code == 405


# ==========================================
# /chat/{session_id} DELETE ADVERSARIAL TESTS
# ==========================================

@pytest.mark.asyncio
async def test_delete_chat_non_existent():
    """Verify that deleting a non-existent session_id returns 200 success without crashing."""
    session_id = f"non-existent-session-{uuid.uuid4()}"
    async with get_client() as client:
        response = await client.delete(f"/api/v1/chat/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

@pytest.mark.asyncio
async def test_delete_chat_invalid_method():
    """Verify that GET/POST on /chat/{session_id} returns 405 Method Not Allowed."""
    session_id = "some-session-id"
    async with get_client() as client:
        response = await client.get(f"/api/v1/chat/{session_id}")
    assert response.status_code == 405


# ==========================================
# /session/migrate ENDPOINT ADVERSARIAL TESTS
# ==========================================

@pytest.mark.asyncio
async def test_session_migrate_non_existent_user():
    """Verify that migrating to a valid UUID format but non-existent user_id results in a 400 error."""
    guest_session_id = f"guest-{uuid.uuid4()}"
    non_existent_user_uuid = uuid.uuid4()
    
    # Create the conversation first to migrate
    async with AsyncSessionLocal() as session:
        conv = Conversation(session_id=guest_session_id, title="Guest Chat")
        session.add(conv)
        await session.commit()

    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/migrate",
            json={
                "guest_session_id": guest_session_id,
                "user_id": str(non_existent_user_uuid)
            }
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "User does not exist"

@pytest.mark.asyncio
async def test_session_migrate_invalid_uuid_format():
    """Verify that migrating to an invalid UUID format returns 400 Bad Request."""
    guest_session_id = f"guest-{uuid.uuid4()}"
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/migrate",
            json={
                "guest_session_id": guest_session_id,
                "user_id": "invalid-uuid"
            }
        )
    assert response.status_code == 400
    data = response.json()
    assert "Invalid user_id format" in data["detail"]

@pytest.mark.asyncio
async def test_session_migrate_invalid_method():
    """Verify that GET on /session/migrate returns 405 Method Not Allowed."""
    async with get_client() as client:
        response = await client.get("/api/v1/session/migrate")
    assert response.status_code == 405
