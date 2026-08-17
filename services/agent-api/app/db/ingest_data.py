import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.db.postgres import engine, AsyncSessionLocal
from app.db.models import Base, Ingredient, LiquorPrice, MixologyRule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ingest_data")

REPO_ROOT = Path(__file__).resolve().parents[4]
CLEANED_DATA_DIR = REPO_ROOT / "pipelines" / "knowledge-base" / "data" / "cleaned"


class DestructiveSyncNotAllowedError(RuntimeError):
    """Raised when a destructive reference-data sync targets a database that
    is not confirmed to be an isolated test database."""


async def run_schema_migrations() -> None:
    """Create/upgrade tables, indexes, checks, foreign keys and triggers.

    This never reads or writes reference-data rows, so it is safe to call
    on every startup: table creation is idempotent (SQLAlchemy checks for
    existing tables first) and the conversations upgrade below only adds
    columns/constraints/triggers if they are missing.
    """
    async with engine.begin() as conn:
        logger.info("Creating database tables if they do not exist...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully.")

        if conn.dialect.name == "postgresql":
            await _migrate_conversations_schema(conn)
            await _ensure_guest_conversation_trigger(conn)


async def _migrate_conversations_schema(conn) -> None:
    logger.info("Upgrading database schema for conversations table...")

    alter_queries = [
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id UUID NULL",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS session_id VARCHAR(255) NULL",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS title VARCHAR(255) DEFAULT 'New Chat'",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ip_hash VARCHAR(255) NULL",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE"
    ]
    for query in alter_queries:
        await conn.execute(text(query))

    # Populate default session_id and set NOT NULL if nullable
    check_nullable_sql = """
    SELECT is_nullable
    FROM information_schema.columns
    WHERE table_name = 'conversations'
      AND column_name = 'session_id';
    """
    result_nullable = await conn.execute(text(check_nullable_sql))
    row = result_nullable.fetchone()
    if row and row[0] == "YES":
        await conn.execute(text("UPDATE conversations SET session_id = 'default-session' WHERE session_id IS NULL"))
        await conn.execute(text("ALTER TABLE conversations ALTER COLUMN session_id SET NOT NULL"))

    # Add foreign key constraint if it doesn't exist
    check_fk_sql = """
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_name = 'conversations'
          AND constraint_name = 'fk_conversations_user'
    );
    """
    fk_exists = (await conn.execute(text(check_fk_sql))).scalar()
    if not fk_exists:
        await conn.execute(text("ALTER TABLE conversations ADD CONSTRAINT fk_conversations_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL"))


async def _ensure_guest_conversation_trigger(conn) -> None:
    logger.info("Setting up database triggers...")

    create_func_sql = """
    CREATE OR REPLACE FUNCTION update_conversation_user_id()
    RETURNS TRIGGER AS $$
    BEGIN
        UPDATE conversations
        SET user_id = NEW.id
        WHERE session_id = NEW.guest_session_id AND user_id IS NULL;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
    await conn.execute(text(create_func_sql))

    check_trigger_sql = """
    SELECT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_migrate_guest_conversations'
    );
    """
    result = await conn.execute(text(check_trigger_sql))
    trigger_exists = result.scalar()

    if not trigger_exists:
        create_trigger_sql = """
        CREATE TRIGGER trg_migrate_guest_conversations
        AFTER INSERT ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_conversation_user_id();
        """
        await conn.execute(text(create_trigger_sql))
        logger.info("Trigger 'trg_migrate_guest_conversations' created.")
    else:
        logger.info("Trigger 'trg_migrate_guest_conversations' already exists.")


def _load_cleaned_dataset(filename: str):
    path = CLEANED_DATA_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def _upsert_ingredients(session, ingredients_data) -> None:
    logger.info(f"Ingesting {len(ingredients_data)} ingredients...")
    ingredient_vals = [
        {
            "id": str(item["id"]),
            "name": item["name"],
            "description": item.get("description"),
            "type": item.get("type"),
            "is_alcoholic": item.get("is_alcoholic", False),
            "abv": item.get("abv")
        }
        for item in ingredients_data
    ]
    if ingredient_vals:
        stmt_ing = insert(Ingredient).values(ingredient_vals)
        stmt_ing = stmt_ing.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt_ing.excluded.name,
                "description": stmt_ing.excluded.description,
                "type": stmt_ing.excluded.type,
                "is_alcoholic": stmt_ing.excluded.is_alcoholic,
                "abv": stmt_ing.excluded.abv
            }
        )
        await session.execute(stmt_ing)
    logger.info("Ingredients ingestion completed.")


async def _upsert_liquor_prices(session, liquor_prices_data) -> None:
    """Upsert by the (name, size_raw) stable key.

    Never deletes: a row a bar added by hand, or any row not present in
    this run's JSON payload, is left untouched.
    """
    logger.info(f"Upserting {len(liquor_prices_data)} liquor prices...")
    liquor_price_vals = [
        {
            "name": item["name"],
            "category": item["category"],
            "size_raw": item["size_raw"],
            "size_ml": item["size_ml"],
            "price_vnd": float(item["price_vnd"]),
            "price_per_ml_vnd": float(item["price_per_ml_vnd"])
        }
        for item in liquor_prices_data
    ]
    if liquor_price_vals:
        stmt_price = insert(LiquorPrice).values(liquor_price_vals)
        stmt_price = stmt_price.on_conflict_do_update(
            index_elements=["name", "size_raw"],
            set_={
                "category": stmt_price.excluded.category,
                "size_ml": stmt_price.excluded.size_ml,
                "price_vnd": stmt_price.excluded.price_vnd,
                "price_per_ml_vnd": stmt_price.excluded.price_per_ml_vnd,
            }
        )
        await session.execute(stmt_price)
    logger.info("Liquor prices ingestion completed.")


async def _upsert_mixology_rules(session, mixology_data) -> None:
    substitutions = mixology_data.get("substitutions", [])
    logger.info(f"Ingesting {len(substitutions)} mixology rules...")
    mixology_vals = [
        {
            "ingredient": item["ingredient"],
            "substitutes": item["substitutes"],
            "notes": item.get("notes")
        }
        for item in substitutions
    ]
    if mixology_vals:
        stmt_mix = insert(MixologyRule).values(mixology_vals)
        stmt_mix = stmt_mix.on_conflict_do_update(
            index_elements=["ingredient"],
            set_={
                "substitutes": stmt_mix.excluded.substitutes,
                "notes": stmt_mix.excluded.notes
            }
        )
        await session.execute(stmt_mix)
    logger.info("Mixology rules ingestion completed.")


async def ingest_reference_data() -> None:
    """Idempotently upsert ingredients, liquor prices and mixology rules.

    Assumes run_schema_migrations() has already created the tables. Every
    write is a keyed upsert; nothing is deleted.
    """
    logger.info(f"Loading data from directory: {CLEANED_DATA_DIR}")
    ingredients_data = _load_cleaned_dataset("ingredients.json")
    liquor_prices_data = _load_cleaned_dataset("liquor_prices.json")
    mixology_data = _load_cleaned_dataset("mixology_data.json")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _upsert_ingredients(session, ingredients_data)
            await _upsert_liquor_prices(session, liquor_prices_data)
            await _upsert_mixology_rules(session, mixology_data)


def _is_isolated_test_database() -> bool:
    """Best-effort guard for the one operation allowed to delete reference rows.

    Mirrors the FND-03 fail-closed posture: refuse unless the configured
    database is unambiguously a disposable test database (the CI job names
    its Postgres service `pourmind_test`), never the shared/dev database the
    default .env points at.
    """
    if settings.APP_ENV == "production":
        return False
    return "test" in (settings.POSTGRES_DB or "").lower()


async def sync_reference_data_full(*, confirm_isolated_test_db: bool = False) -> None:
    """Destructive full resync: liquor_prices ends up exactly matching the
    shipped JSON, deleting any row absent from it.

    This is the only function in the module that deletes reference-data
    rows, and it is intentionally separate from the idempotent upsert path
    used on every startup. It fails closed unless the caller explicitly
    opts in AND the configured database is recognizably an isolated test
    database.
    """
    if not confirm_isolated_test_db or not _is_isolated_test_database():
        raise DestructiveSyncNotAllowedError(
            "Destructive reference-data sync refused: target database is not "
            "confirmed to be an isolated test database"
        )

    liquor_prices_data = _load_cleaned_dataset("liquor_prices.json")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(LiquorPrice))
            session.add_all([
                LiquorPrice(
                    name=item["name"],
                    category=item["category"],
                    size_raw=item["size_raw"],
                    size_ml=item["size_ml"],
                    price_vnd=float(item["price_vnd"]),
                    price_per_ml_vnd=float(item["price_per_ml_vnd"])
                )
                for item in liquor_prices_data
            ])
    logger.info("Destructive liquor_prices resync completed.")


async def ingest_data() -> None:
    """Backward-compatible full pipeline: schema migration + reference-data
    ingestion. Kept for local/manual runs (`python -m app.db.ingest_data`);
    tests should call run_schema_migrations() or ingest_reference_data()
    directly instead of the combined pipeline."""
    await run_schema_migrations()
    await ingest_reference_data()


if __name__ == "__main__":
    asyncio.run(ingest_data())
