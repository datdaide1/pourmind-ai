import pytest
import uuid
from sqlalchemy import select
from app.db.postgres import AsyncSessionLocal
from app.db.models import User, Conversation, LiquorPrice
from app.db.ingest_data import DestructiveSyncNotAllowedError, run_schema_migrations, sync_reference_data_full

@pytest.fixture(scope="module", autouse=True)
async def setup_db_and_triggers():
    # Initialize the database schema and triggers only. Migration tests must
    # not invoke the full ingestion pipeline (it needs the shipped JSON
    # dataset and is exercised independently in tests/test_ingest_data.py).
    await run_schema_migrations()

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


@pytest.mark.asyncio
async def test_reapplying_migrations_preserves_existing_liquor_prices():
    marker_name = f"migration-test-liquor-{uuid.uuid4()}"

    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add(
                LiquorPrice(
                    name=marker_name,
                    category="Test",
                    size_raw="700ml",
                    size_ml=700,
                    price_vnd=100000.0,
                    price_per_ml_vnd=142.86,
                )
            )

    try:
        # Reapplying schema migrations must never touch reference-data rows.
        await run_schema_migrations()
        await run_schema_migrations()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(LiquorPrice).where(LiquorPrice.name == marker_name)
            )
            row = result.scalar_one()
            assert row.price_vnd == 100000.0
    finally:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(LiquorPrice).where(LiquorPrice.name == marker_name)
                )
                existing = result.scalar_one_or_none()
                if existing is not None:
                    await session.delete(existing)


@pytest.mark.asyncio
async def test_destructive_resync_refused_without_explicit_confirmation():
    with pytest.raises(DestructiveSyncNotAllowedError):
        await sync_reference_data_full()


@pytest.mark.asyncio
async def test_destructive_resync_refused_against_non_test_database(monkeypatch):
    from app.db import ingest_data as ingest_data_module

    monkeypatch.setattr(ingest_data_module.settings, "POSTGRES_DB", "postgres")
    monkeypatch.setattr(ingest_data_module.settings, "APP_ENV", "local")

    with pytest.raises(DestructiveSyncNotAllowedError):
        await sync_reference_data_full(confirm_isolated_test_db=True)


@pytest.mark.asyncio
async def test_destructive_resync_refused_in_production(monkeypatch):
    from app.db import ingest_data as ingest_data_module

    monkeypatch.setattr(ingest_data_module.settings, "POSTGRES_DB", "pourmind_test")
    monkeypatch.setattr(ingest_data_module.settings, "APP_ENV", "production")

    with pytest.raises(DestructiveSyncNotAllowedError):
        await sync_reference_data_full(confirm_isolated_test_db=True)
