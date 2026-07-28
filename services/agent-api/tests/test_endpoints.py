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
    # Mock get_relevant_venues and get_relevant_cocktails
    with patch("app.api.endpoints.get_relevant_venues", new_callable=AsyncMock) as mock_venues, \
         patch("app.api.endpoints.get_relevant_cocktails", new_callable=AsyncMock) as mock_cocktails:
        mock_venues.return_value = [{"name": "Mock Venue", "address": "123 Street", "rating": 4.5}]
        mock_cocktails.return_value = [{"name": "Mock Cocktail", "alcoholic_type": "Alcoholic"}]
        yield

@pytest.mark.asyncio
async def test_session_init_new():
    session_id = f"test-init-{uuid.uuid4()}"
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/init",
            json={
                "guest_session_id": session_id,
                "mode": "guest"
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "welcome_message" in data
    assert "suggested_prompts" in data
    
    # Verify created in DB
    async with AsyncSessionLocal() as session:
        conv = (await session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )).scalar_one_or_none()
        assert conv is not None
        assert conv.metadata_["mode"] == "guest"

@pytest.mark.asyncio
async def test_session_init_bartender():
    session_id = f"test-init-{uuid.uuid4()}"
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/init",
            json={
                "guest_session_id": session_id,
                "mode": "bartender"
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert "Master Bartender" in data["welcome_message"]

@pytest.mark.asyncio
async def test_chat_message_streaming():
    session_id = f"test-chat-{uuid.uuid4()}"
    
    # 1. Initialize session
    async with get_client() as client:
        await client.post(
            "/api/v1/session/init",
            json={"guest_session_id": session_id, "mode": "guest"}
        )
    
    # Mock graph.astream_events
    mock_events = [
        {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Mocked ")}},
        {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="token.")}},
        {
            "event": "on_chain_end",
            "parent_ids": [],
            "data": {
                "output": {
                    "intent": "b2c",
                    "messages": [
                        HumanMessage(content="test query"),
                        AIMessage(content="Mocked token.")
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
                    "content": "Make me something fresh",
                    "context": {
                        "current_location": {"lat": 10.7, "lng": 106.6}
                    }
                }
            )
        assert response.status_code == 200
        text = response.text
        assert "Mocked" in text
        assert "token." in text
        assert "ui_blocks" in text
        
        # Verify messages saved to database
        async with AsyncSessionLocal() as session:
            stmt = select(Conversation).where(
                Conversation.session_id == session_id
            ).options(selectinload(Conversation.messages))
            conv = (await session.execute(stmt)).scalar_one_or_none()
            assert conv is not None
            assert len(conv.messages) == 2
            assert conv.messages[0].role == "user"
            assert conv.messages[1].role == "assistant"
            assert conv.messages[1].ui_blocks is not None

@pytest.mark.asyncio
async def test_calculate_cost_endpoint():
    # Mock calculate_cost_and_abv
    with patch("app.api.endpoints.calculate_cost_and_abv", new_callable=AsyncMock) as mock_calc:
        mock_calc.return_value = {
            "total_cost_vnd": 15000.0,
            "abv": 15.5,
            "total_volume_ml": 60.0,
            "breakdown": []
        }
        async with get_client() as client:
            response = await client.post(
                "/api/v1/tools/calculate_cost",
                json={
                    "recipe": [
                        {"ingredient": "Vodka", "amount_ml": 45.0},
                        {"ingredient": "Lime Juice", "amount_ml": 15.0}
                    ]
                }
            )
        assert response.status_code == 200
        data = response.json()
        assert data["total_cost_vnd"] == 15000.0
        assert data["estimated_abv"] == 15.5
        assert data["total_volume_ml"] == 60.0

@pytest.mark.asyncio
async def test_chat_history_and_delete():
    user_uuid = uuid.uuid4()
    session_id = f"test-hist-{uuid.uuid4()}"
    
    # 0. Insert User into database first to prevent foreign key violation
    async with AsyncSessionLocal() as session:
        user = User(id=user_uuid, guest_session_id=session_id)
        session.add(user)
        await session.commit()
    
    # Init session with user_id
    async with get_client() as client:
        await client.post(
            "/api/v1/session/init",
            json={
                "guest_session_id": session_id,
                "user_id": str(user_uuid),
                "mode": "guest"
            }
        )
    
        # Get history
        response = await client.get(f"/api/v1/chat/history?user_id={user_uuid}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["session_id"] == session_id
        
        # Delete chat
        del_response = await client.delete(f"/api/v1/chat/{session_id}")
        assert del_response.status_code == 200
        assert del_response.json()["success"] is True
        
        # History should be empty now
        response = await client.get(f"/api/v1/chat/history?user_id={user_uuid}")
        assert response.status_code == 200
        assert len(response.json()["conversations"]) == 0

@pytest.mark.asyncio
async def test_session_migration():
    guest_session_id = f"guest-{uuid.uuid4()}"
    user_uuid = uuid.uuid4()
    
    # 0. Insert User into database first to prevent foreign key violation
    async with AsyncSessionLocal() as session:
        user = User(id=user_uuid, guest_session_id=guest_session_id)
        session.add(user)
        await session.commit()
    
    # Init guest session
    async with get_client() as client:
        await client.post(
            "/api/v1/session/init",
            json={"guest_session_id": guest_session_id, "mode": "guest"}
        )
        
        # Migrate session
        migrate_response = await client.post(
            "/api/v1/session/migrate",
            json={
                "guest_session_id": guest_session_id,
                "user_id": str(user_uuid)
            }
        )
        assert migrate_response.status_code == 200
        assert migrate_response.json()["success"] is True
    
    # Check that the conversation user_id is now updated
    async with AsyncSessionLocal() as session:
        conv = (await session.execute(
            select(Conversation).where(Conversation.session_id == guest_session_id)
        )).scalar_one_or_none()
        assert conv is not None
        assert conv.user_id == user_uuid
