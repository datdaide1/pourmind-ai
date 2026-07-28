import asyncio
import json
import os
import logging
from pathlib import Path
from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert
from app.db.postgres import engine, AsyncSessionLocal
from app.db.models import Base, Ingredient, LiquorPrice, MixologyRule, User, Conversation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ingest_data")

async def ingest_data():
    logger.info("Starting database ingestion process...")

    # 1. Create tables
    async with engine.begin() as conn:
        logger.info("Creating database tables if they do not exist...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully.")

        # Create Postgres trigger if using postgresql dialect
        if conn.dialect.name == "postgresql":
            logger.info("Upgrading database schema for conversations table...")
            
            # Alter table conversations
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

            logger.info("Setting up database triggers...")
            
            # Create or replace function
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
            
            # Check if trigger exists
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

    # Locate paths for cleaned data
    repo_root = Path(__file__).resolve().parents[4]
    cleaned_data_dir = repo_root / "pipelines" / "knowledge-base" / "data" / "cleaned"

    ingredients_path = cleaned_data_dir / "ingredients.json"
    liquor_prices_path = cleaned_data_dir / "liquor_prices.json"
    mixology_path = cleaned_data_dir / "mixology_data.json"

    logger.info(f"Loading data from directory: {cleaned_data_dir}")

    # Load JSON files
    with open(ingredients_path, "r", encoding="utf-8") as f:
        ingredients_data = json.load(f)
    
    with open(liquor_prices_path, "r", encoding="utf-8") as f:
        liquor_prices_data = json.load(f)
        
    with open(mixology_path, "r", encoding="utf-8") as f:
        mixology_data = json.load(f)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 2. Ingest Ingredients (idempotent upsert)
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

            # 3. Ingest Liquor Prices (delete and insert for simplicity and idempotency)
            logger.info(f"Ingesting {len(liquor_prices_data)} liquor prices...")
            await session.execute(delete(LiquorPrice))
            
            liquor_price_objects = [
                LiquorPrice(
                    name=item["name"],
                    category=item["category"],
                    size_raw=item["size_raw"],
                    size_ml=item["size_ml"],
                    price_vnd=float(item["price_vnd"]),
                    price_per_ml_vnd=float(item["price_per_ml_vnd"])
                )
                for item in liquor_prices_data
            ]
            session.add_all(liquor_price_objects)
            logger.info("Liquor prices ingestion completed.")

            # 4. Ingest Mixology Rules (idempotent upsert)
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

    logger.info("Database ingestion process completed successfully.")

if __name__ == "__main__":
    asyncio.run(ingest_data())
