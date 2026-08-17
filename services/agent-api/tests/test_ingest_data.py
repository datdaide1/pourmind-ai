import uuid

import pytest
from sqlalchemy import select

from app.db.ingest_data import (
    _load_cleaned_dataset,
    ingest_reference_data,
    run_schema_migrations,
    sync_reference_data_full,
)
from app.db.models import LiquorPrice, MixologyRule
from app.db.postgres import AsyncSessionLocal


@pytest.fixture(scope="module", autouse=True)
async def setup_schema():
    # Reference-data ingestion is callable independently of the JSON
    # pipeline's schema step; the fixture only needs the tables to exist.
    await run_schema_migrations()


@pytest.mark.asyncio
async def test_ingest_reference_data_is_idempotent():
    liquor_prices_data = _load_cleaned_dataset("liquor_prices.json")

    await ingest_reference_data()
    async with AsyncSessionLocal() as session:
        count_after_first = (await session.execute(select(LiquorPrice))).scalars().all()

    await ingest_reference_data()
    async with AsyncSessionLocal() as session:
        count_after_second = (await session.execute(select(LiquorPrice))).scalars().all()

    # Re-running ingestion updates matching rows in place; it must not grow
    # the table by re-inserting the same shipped dataset.
    assert len(count_after_first) == len(count_after_second)
    assert len(count_after_second) >= len(liquor_prices_data)


@pytest.mark.asyncio
async def test_liquor_price_upsert_preserves_unrelated_rows_and_updates_matching_key():
    marker_name = f"ingest-test-liquor-{uuid.uuid4()}"

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # A row a bar added by hand: not present in the shipped JSON.
            session.add(
                LiquorPrice(
                    name=marker_name,
                    category="Test",
                    size_raw="700ml",
                    size_ml=700,
                    price_vnd=1.0,
                    price_per_ml_vnd=0.0014,
                )
            )

    try:
        await ingest_reference_data()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(LiquorPrice).where(LiquorPrice.name == marker_name)
            )
            preserved = result.scalar_one()
            assert preserved.price_vnd == 1.0

        # Re-ingest with an updated price for an existing (name, size_raw)
        # key and confirm it updates in place rather than duplicating.
        liquor_prices_data = _load_cleaned_dataset("liquor_prices.json")
        sample = liquor_prices_data[0]
        updated_price = float(sample["price_vnd"]) + 12345.0

        async with AsyncSessionLocal() as session:
            async with session.begin():
                from sqlalchemy.dialects.postgresql import insert

                stmt = insert(LiquorPrice).values(
                    name=sample["name"],
                    category=sample["category"],
                    size_raw=sample["size_raw"],
                    size_ml=sample["size_ml"],
                    price_vnd=updated_price,
                    price_per_ml_vnd=float(sample["price_per_ml_vnd"]),
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["name", "size_raw"],
                    set_={"price_vnd": stmt.excluded.price_vnd},
                )
                await session.execute(stmt)

        await ingest_reference_data()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(LiquorPrice).where(
                    LiquorPrice.name == sample["name"],
                    LiquorPrice.size_raw == sample["size_raw"],
                )
            )
            rows = result.scalars().all()
            # The stable key must resolve to exactly one row, restored to
            # the shipped dataset's price by the second ingest call.
            assert len(rows) == 1
            assert rows[0].price_vnd == float(sample["price_vnd"])
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
async def test_ingest_mixology_rules_upserts_without_duplicating():
    await ingest_reference_data()
    async with AsyncSessionLocal() as session:
        first_pass = (await session.execute(select(MixologyRule))).scalars().all()

    await ingest_reference_data()
    async with AsyncSessionLocal() as session:
        second_pass = (await session.execute(select(MixologyRule))).scalars().all()

    assert len(first_pass) == len(second_pass)


@pytest.mark.asyncio
async def test_sync_reference_data_full_is_destructive_and_fails_closed_by_default():
    from app.db.ingest_data import DestructiveSyncNotAllowedError

    with pytest.raises(DestructiveSyncNotAllowedError):
        await sync_reference_data_full()

    # The refusal must happen before any row is touched.
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(LiquorPrice))).scalars().all()
        assert len(rows) > 0
