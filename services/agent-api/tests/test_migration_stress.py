import pytest
import uuid
import asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.db.postgres import AsyncSessionLocal
from app.db.models import Conversation, User

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

@pytest.mark.asyncio
async def test_migrate_non_existent_session_id():
    # 1. Non-existent session ID with a valid user
    user_uuid = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        user = User(id=user_uuid, guest_session_id=None)
        session.add(user)
        await session.commit()

    non_existent_session = f"non-existent-{uuid.uuid4()}"
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/migrate",
            json={
                "guest_session_id": non_existent_session,
                "user_id": str(user_uuid)
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Conversations migrated successfully" in data["message"]

@pytest.mark.asyncio
async def test_migrate_non_existent_user_id():
    # 2. Existing session ID with a non-existent user ID
    guest_session_id = f"guest-{uuid.uuid4()}"
    async with AsyncSessionLocal() as session:
        conv = Conversation(
            session_id=guest_session_id,
            title="Temp Chat",
            user_id=None
        )
        session.add(conv)
        await session.commit()

    non_existent_user_uuid = uuid.uuid4()
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/migrate",
            json={
                "guest_session_id": guest_session_id,
                "user_id": str(non_existent_user_uuid)
            }
        )
    # Since there's a foreign key constraint to users(id), this should fail with 400 Bad Request
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_migrate_invalid_user_id_format():
    # 3. Invalid user ID format
    async with get_client() as client:
        response = await client.post(
            "/api/v1/session/migrate",
            json={
                "guest_session_id": "some-session",
                "user_id": "invalid-uuid"
            }
        )
    assert response.status_code == 400
    assert "Invalid user_id format" in response.json()["detail"]

@pytest.mark.asyncio
async def test_concurrent_session_migrations():
    # Create guest session conversation
    guest_session_id = f"guest-concurrent-{uuid.uuid4()}"
    async with AsyncSessionLocal() as db_session:
        conv = Conversation(
            session_id=guest_session_id,
            title="Concurrent Migrate Chat",
            user_id=None
        )
        db_session.add(conv)
        await db_session.commit()

    # Create 5 distinct users
    user_ids = [uuid.uuid4() for _ in range(5)]
    async with AsyncSessionLocal() as db_session:
        for u_id in user_ids:
            user = User(id=u_id, guest_session_id=guest_session_id)
            db_session.add(user)
        await db_session.commit()

    # Send concurrent migration requests
    async def migrate_request(u_id):
        async with get_client() as client:
            return await client.post(
                "/api/v1/session/migrate",
                json={
                    "guest_session_id": guest_session_id,
                    "user_id": str(u_id)
                }
            )

    tasks = [migrate_request(u_id) for u_id in user_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify that all operations succeeded without deadlock (each returning 200 or failure)
    successes = 0
    failures = 0
    for res in results:
        if isinstance(res, Exception):
            failures += 1
        elif res.status_code == 200:
            successes += 1
        else:
            failures += 1

    # Check database status
    async with AsyncSessionLocal() as db_session:
        # Re-fetch conversation
        stmt = select(Conversation).where(Conversation.session_id == guest_session_id)
        res = await db_session.execute(stmt)
        updated_conv = res.scalar_one()
        assert updated_conv.user_id in user_ids
        
    print(f"Concurrent migration test: successes={successes}, failures={failures}")

@pytest.mark.asyncio
async def test_concurrent_user_inserts_trigger():
    # Test DB trigger behavior when inserting multiple users concurrently with the same guest_session_id
    guest_session_id = f"guest-trigger-concurrent-{uuid.uuid4()}"
    async with AsyncSessionLocal() as db_session:
        conv = Conversation(
            session_id=guest_session_id,
            title="Trigger Concurrent Chat",
            user_id=None
        )
        db_session.add(conv)
        await db_session.commit()

    # Define tasks to insert Users concurrently in separate transactions
    async def insert_user(u_id):
        async with AsyncSessionLocal() as db_session:
            user = User(id=u_id, guest_session_id=guest_session_id)
            db_session.add(user)
            await db_session.commit()

    user_ids = [uuid.uuid4() for _ in range(5)]
    tasks = [insert_user(u_id) for u_id in user_ids]
    
    # Run them concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check if any errors occurred
    exceptions = [r for r in results if isinstance(r, Exception)]
    
    # Re-fetch conversation to see what user_id it got
    async with AsyncSessionLocal() as db_session:
        stmt = select(Conversation).where(Conversation.session_id == guest_session_id)
        res = await db_session.execute(stmt)
        updated_conv = res.scalar_one()
        # Verify the conversation is now owned by one of the users
        assert updated_conv.user_id in user_ids
        
    print(f"Concurrent inserts trigger test: exceptions count={len(exceptions)}")
