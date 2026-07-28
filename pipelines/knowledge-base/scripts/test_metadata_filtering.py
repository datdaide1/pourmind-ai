import os
import sys
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(REPO_ROOT / "services" / "agent-api"))
from app.core.config import settings

def main():
    print("=== Starting Qdrant Metadata Filtering Gateway Test ===")
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    
    # Generate a dummy vector for pure filtering search
    # text-embedding-3-small dimension is 1536
    dummy_vector = [0.0] * 1536
    
    passed_tests = 0
    total_tests = 0

    print("\n--- Test 1: Venues Filtering (City) ---")
    city_filter = "Ho Chi Minh City"
    venues_res = client.search(
        collection_name="venues",
        query_vector=dummy_vector,
        query_filter=models.Filter(
            must=[models.FieldCondition(key="city", match=models.MatchValue(value=city_filter))]
        ),
        limit=50
    )
    total_tests += 1
    if len(venues_res) > 0:
        all_match = all(hit.payload.get("city") == city_filter for hit in venues_res)
        assert all_match, f"Failed: Found venues not in {city_filter}"
        print(f"Pass: Retrieved {len(venues_res)} venues. 100% accurately matched city='{city_filter}'.")
        passed_tests += 1
    else:
        print("Warning: No venues found for filter. Cannot verify accuracy.")

    print("\n--- Test 2: Cocktails Filtering (Base Liquor) ---")
    liquor_filter = "Gin"
    cocktails_res = client.search(
        collection_name="cocktails",
        query_vector=dummy_vector,
        query_filter=models.Filter(
            must=[models.FieldCondition(key="base_liquor", match=models.MatchValue(value=liquor_filter))]
        ),
        limit=50
    )
    total_tests += 1
    if len(cocktails_res) > 0:
        all_match = all(hit.payload.get("base_liquor") == liquor_filter for hit in cocktails_res)
        assert all_match, f"Failed: Found cocktails without base_liquor='{liquor_filter}'"
        print(f"Pass: Retrieved {len(cocktails_res)} cocktails. 100% accurately matched base_liquor='{liquor_filter}'.")
        passed_tests += 1
    else:
        print("Warning: No cocktails found for filter. Cannot verify accuracy.")

    print(f"\n=== Gateway Test Result: {passed_tests}/{total_tests} Tests Passed ===")
    if passed_tests == total_tests:
        print("Gateway Condition: ACHIEVED (100% Filtering Accuracy)")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
