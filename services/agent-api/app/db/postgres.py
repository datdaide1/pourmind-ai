import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create the async engine
engine = create_async_engine(
    settings.postgres_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={
        "ssl": "require",
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: ""
    }
)

# Create an async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

async def check_postgres_connection() -> bool:
    """Verifies the connection to the PostgreSQL database."""
    try:
        async with engine.connect() as conn:
            # Execute a simple query
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to PostgreSQL (Supabase).")
            return True
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return False
