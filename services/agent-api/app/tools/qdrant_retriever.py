import logging
from typing import List, Dict, Any
from qdrant_client import AsyncQdrantClient
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Qdrant Client (Async)
try:
    qdrant_client = AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )
except Exception as e:
    logger.error(f"Failed to initialize Qdrant Client: {e}")
    qdrant_client = None

# Initialize Embeddings model
try:
    embeddings_model = OpenAIEmbeddings(
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=settings.OPENROUTER_API_KEY,
        model="openai/text-embedding-3-small"
    )
except Exception as e:
    logger.error(f"Failed to initialize OpenAI Embeddings: {e}")
    embeddings_model = None


async def search_qdrant(query: str, collection_name: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Search a specified Qdrant collection using the query string.
    """
    if not qdrant_client or not embeddings_model:
        logger.error("Qdrant client or Embeddings model is not initialized.")
        return []

    try:
        # Generate query embedding
        query_vector = await embeddings_model.aembed_query(query)
        
        # Search Qdrant
        search_results = await qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True
        )
        
        # Extract payloads
        results = [point.payload for point in search_results if point.payload]
        return results
    except Exception as e:
        logger.error(f"Error searching Qdrant collection '{collection_name}': {e}")
        return []


async def get_relevant_cocktails(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve relevant cocktails from the Qdrant Vector DB based on a query.
    Returns a list of payloads containing cocktail details.
    """
    logger.info(f"Retrieving cocktails for query: '{query}'")
    return await search_qdrant(query, collection_name="cocktails", limit=limit)


async def get_relevant_venues(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve relevant venues from the Qdrant Vector DB based on a query.
    Returns a list of payloads containing venue details.
    """
    logger.info(f"Retrieving venues for query: '{query}'")
    return await search_qdrant(query, collection_name="venues", limit=limit)
