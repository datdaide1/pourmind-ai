import logging
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create the async Redis client for Upstash
redis_url = f"rediss://default:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}"
redis_client = redis.Redis.from_url(
    redis_url,
    decode_responses=True
)

async def check_redis_connection() -> bool:
    """Verifies the connection to Upstash Redis."""
    try:
        ping = await redis_client.ping()
        if ping:
            logger.info("Successfully connected to Upstash Redis.")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return False
