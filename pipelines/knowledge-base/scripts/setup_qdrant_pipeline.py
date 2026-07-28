import os
import json
import uuid
import sys
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models
REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT / "services" / "agent-api"))
from app.core.config import settings

# Keep model caches inside the local repository workspace.
os.environ["HF_HOME"] = str(REPO_ROOT / ".cache" / "huggingface")
os.environ["TRANSFORMERS_CACHE"] = str(REPO_ROOT / ".cache" / "huggingface")

# Load OpenRouter embedding model
from langchain_openai import OpenAIEmbeddings

# Cleaned data files paths
CLEANED_DIR = PIPELINE_ROOT / "data" / "cleaned"
VENUES_FILE = os.path.join(CLEANED_DIR, "venues.json")
COCKTAILS_FILE = os.path.join(CLEANED_DIR, "cocktails.json")

def main():
    # 1. Initialize OpenRouter Embeddings model
    print("Loading OpenRouter Embeddings model 'openai/text-embedding-3-small'...")
    model = OpenAIEmbeddings(
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=settings.OPENROUTER_API_KEY,
        model="openai/text-embedding-3-small"
    )
    vector_size = 1536
    print(f"Model loaded. Vector dimension: {vector_size}")

    # 2. Initialize Qdrant Client
    print(f"Connecting to Qdrant Cloud at: {settings.QDRANT_URL}")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )

    # 3. Create 'venues' collection
    col_venues = "venues"
    print(f"Recreating collection '{col_venues}'...")
    collections = client.get_collections().collections
    existing_names = [col.name for col in collections]
    if col_venues in existing_names:
        client.delete_collection(col_venues)
        print(f"Deleted existing '{col_venues}' collection.")
        
    client.create_collection(
        collection_name=col_venues,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE
        )
    )
    print(f"Created collection '{col_venues}'.")

    # Configure payload indexes for 'venues'
    print(f"Creating payload indexes for '{col_venues}'...")
    client.create_payload_index(
        collection_name=col_venues,
        field_name="city",
        field_schema=models.PayloadSchemaType.KEYWORD
    )
    client.create_payload_index(
        collection_name=col_venues,
        field_name="district",
        field_schema=models.PayloadSchemaType.KEYWORD
    )
    client.create_payload_index(
        collection_name=col_venues,
        field_name="rating",
        field_schema=models.PayloadSchemaType.FLOAT
    )
    print(f"Payload indexes created for '{col_venues}'.")

    # 4. Create 'cocktails' collection
    col_cocktails = "cocktails"
    print(f"Recreating collection '{col_cocktails}'...")
    if col_cocktails in existing_names:
        client.delete_collection(col_cocktails)
        print(f"Deleted existing '{col_cocktails}' collection.")
        
    client.create_collection(
        collection_name=col_cocktails,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE
        )
    )
    print(f"Created collection '{col_cocktails}'.")

    # Configure payload indexes for 'cocktails'
    print(f"Creating payload indexes for '{col_cocktails}'...")
    client.create_payload_index(
        collection_name=col_cocktails,
        field_name="alcoholic_type",
        field_schema=models.PayloadSchemaType.KEYWORD
    )
    client.create_payload_index(
        collection_name=col_cocktails,
        field_name="base_liquor",
        field_schema=models.PayloadSchemaType.KEYWORD
    )
    print(f"Payload indexes created for '{col_cocktails}'.")

    # 5. Populate 'venues' collection
    print(f"Loading venues from: {VENUES_FILE}")
    with open(VENUES_FILE, "r", encoding="utf-8") as f:
        venues = json.load(f)

    print("Generating embeddings and preparing points for venues...")
    text_reps = []
    for v in venues:
        vibe_str = v["reviews"][0] if v["reviews"] else "Unknown vibe"
        text_reps.append(f"Venue: {v['name']} | City: {v['city']} | District: {v['district']} | Address: {v['address']} | Vibe: {vibe_str} | Rating: {v['rating']}")
    
    # Batch embedding
    vectors = model.embed_documents(text_reps)
    
    venue_points = []
    for v, vector in zip(venues, vectors):
        qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, v["id"]))
        venue_points.append(models.PointStruct(
            id=qdrant_id,
            vector=vector,
            payload={
                "id": v["id"],
                "name": v["name"],
                "city": v["city"],
                "district": v["district"],
                "address": v["address"],
                "rating": v["rating"],
                "reviews": v["reviews"]
            }
        ))
        
    print(f"Upserting {len(venue_points)} venues to Qdrant...")
    # Upsert in chunks
    chunk_size = 50
    for i in range(0, len(venue_points), chunk_size):
        chunk = venue_points[i:i+chunk_size]
        client.upsert(
            collection_name=col_venues,
            points=chunk
        )
    print(f"Successfully upserted all venues.")

    # 6. Populate 'cocktails' collection
    print(f"Loading cocktails from: {COCKTAILS_FILE}")
    with open(COCKTAILS_FILE, "r", encoding="utf-8") as f:
        cocktails = json.load(f)

    print("Generating embeddings and preparing points for cocktails...")
    text_reps = []
    for c in cocktails:
        ing_str = ", ".join(c["ingredients"])
        text_reps.append(f"Cocktail: {c['name']} | Type: {c['alcoholic_type']} | Base Liquor: {c['base_liquor']} | Ingredients: {ing_str} | Instructions: {c['instructions']}")
    
    # Batch embedding
    vectors = model.embed_documents(text_reps)
    
    cocktail_points = []
    for c, vector in zip(cocktails, vectors):
        try:
            qdrant_id = int(c["id"])
        except ValueError:
            qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, c["id"]))
            
        cocktail_points.append(models.PointStruct(
            id=qdrant_id,
            vector=vector,
            payload={
                "id": c["id"],
                "name": c["name"],
                "alcoholic_type": c["alcoholic_type"],
                "base_liquor": c["base_liquor"],
                "ingredients": c["ingredients"],
                "instructions": c["instructions"],
                "price": c["price"]
            }
        ))
        
    print(f"Upserting {len(cocktail_points)} cocktails to Qdrant...")
    for i in range(0, len(cocktail_points), chunk_size):
        chunk = cocktail_points[i:i+chunk_size]
        client.upsert(
            collection_name=col_cocktails,
            points=chunk
        )
    print(f"Successfully upserted all cocktails.")
    print("Qdrant Setup & Embedding Pipeline Completed successfully!")

if __name__ == "__main__":
    main()
