import logging
from qdrant_client import AsyncQdrantClient
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize the async Qdrant client
# Since we are using Qdrant Cloud, we need to provide the URL and API Key.
qdrant_client = AsyncQdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
    timeout=10.0
)

async def check_qdrant_connection() -> bool:
    """Verifies the connection to Qdrant Cloud."""
    try:
        # Get the list of collections to verify the connection
        collections = await qdrant_client.get_collections()
        logger.info(f"Successfully connected to Qdrant Cloud. Found {len(collections.collections)} collections.")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant Cloud: {e}")
        return False
