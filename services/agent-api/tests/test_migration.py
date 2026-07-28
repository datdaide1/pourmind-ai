import pytest
import uuid
from sqlalchemy import select
from app.db.postgres import AsyncSessionLocal
from app.db.models import User, Conversation
from app.db.ingest_data import ingest_data

@pytest.fixture(scope="module", autouse=True)
async def setup_db_and_triggers():
    # Initialize the database schema and triggers
    await ingest_data()

@pytest.mark.asyncio
async def test_guest_conversation_migration_trigger():
    session_id = f"test-session-{uuid.uuid4()}"
    user_uuid = uuid.uuid4()
    conv_uuid = uuid.uuid4()

    session = AsyncSessionLocal()
    transaction = await session.begin()
    try:
        # 1. Create a guest conversation without a user_id
        conv = Conversation(
            id=conv_uuid,
            session_id=session_id,
            title="Guest Chat",
            user_id=None
        )
        session.add(conv)
        await session.flush()

        # Check that it exists with user_id as None
        db_conv = await session.get(Conversation, conv_uuid)
        assert db_conv is not None
        assert db_conv.user_id is None

        # 2. Insert the User with the matching guest_session_id
        user = User(
            id=user_uuid,
            guest_session_id=session_id
        )
        session.add(user)
        await session.flush()

        # 3. Refresh/re-fetch the conversation to verify trigger fired and updated user_id
        await session.refresh(db_conv)
        assert db_conv.user_id == user_uuid

    finally:
        # Rollback transaction and close session to keep the database clean
        await transaction.rollback()
        await session.close()
