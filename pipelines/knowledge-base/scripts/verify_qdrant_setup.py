import os
import sys
from pathlib import Path
from qdrant_client import QdrantClient
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(REPO_ROOT / "services" / "agent-api"))
from app.core.config import settings

def main():
    print("=== Starting Qdrant Cloud Setup Verification ===")
    
    # 1. Initialize client
    print(f"Connecting to Qdrant Cloud at: {settings.QDRANT_URL}")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )
    
    # 2. Get collections
    try:
        collections = client.get_collections().collections
        col_names = [col.name for col in collections]
        print(f"Collections found in Qdrant Cloud: {col_names}")
    except Exception as e:
        print(f"Failed to fetch collections from Qdrant: {e}")
        sys.exit(1)
        
    # Assert collections exist
    assert "venues" in col_names, "Assertion Failed: Collection 'venues' does not exist in Qdrant Cloud!"
    assert "cocktails" in col_names, "Assertion Failed: Collection 'cocktails' does not exist in Qdrant Cloud!"
    print("Assertion Passed: Both 'venues' and 'cocktails' collections exist.")
    
    # Get collection details
    venues_info = client.get_collection("venues")
    cocktails_info = client.get_collection("cocktails")
    
    # 3. Assert vector dimensionality matches embedding model (1536)
    venues_vector_size = venues_info.config.params.vectors.size
    cocktails_vector_size = cocktails_info.config.params.vectors.size
    print(f"Venues vector size: {venues_vector_size}")
    print(f"Cocktails vector size: {cocktails_vector_size}")
    
    assert venues_vector_size == 1536, f"Assertion Failed: 'venues' vector size is {venues_vector_size}, expected 1536!"
    assert cocktails_vector_size == 1536, f"Assertion Failed: 'cocktails' vector size is {cocktails_vector_size}, expected 1536!"
    print("Assertion Passed: Vector dimensionality matches model size of 1536.")
    
    # 4. Assert vector count > 0
    venues_count = venues_info.points_count
    cocktails_count = cocktails_info.points_count
    print(f"Venues vector count: {venues_count}")
    print(f"Cocktails vector count: {cocktails_count}")
    
    assert venues_count == 168, f"Assertion Failed: Collection 'venues' contains {venues_count} vectors, expected 168!"
    assert cocktails_count > 0, "Assertion Failed: Collection 'cocktails' contains 0 vectors!"
    print("Assertion Passed: Vector counts are correct (venues count matches 168).")
    
    # 5. Assert metadata payload indexes exist
    venues_schema = venues_info.payload_schema
    cocktails_schema = cocktails_info.payload_schema
    print(f"Venues payload schema indexes: {list(venues_schema.keys())}")
    print(f"Cocktails payload schema indexes: {list(cocktails_schema.keys())}")
    
    # Required venues payload fields
    required_venues_fields = ["city", "district", "rating"]
    for field in required_venues_fields:
        assert field in venues_schema, f"Assertion Failed: Payload index on field '{field}' is missing in 'venues' collection!"
        
    # Required cocktails payload fields
    required_cocktails_fields = ["alcoholic_type", "base_liquor"]
    for field in required_cocktails_fields:
        assert field in cocktails_schema, f"Assertion Failed: Payload index on field '{field}' is missing in 'cocktails' collection!"
        
    print("Assertion Passed: All required payload indexes exist and are configured.")
    print("=== Verification Successful! All Assertions Passed. ===")

if __name__ == "__main__":
    main()
