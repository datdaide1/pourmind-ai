import os
import json
from pathlib import Path

venues_path = Path(__file__).resolve().parents[1] / "data" / "crawled-data" / "venues.json"
with open(venues_path, 'r', encoding='utf-8') as f:
    venues = json.load(f)

ratings = [v['rating'] for v in venues if v.get('rating') is not None]
avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
print(f"Average rating: {avg_rating:.2f}")
print(f"Max rating: {max(ratings) if ratings else 0.0}")
print(f"Min rating: {min(ratings) if ratings else 0.0}")
