import json
import os
from pathlib import Path

pipeline_root = Path(__file__).resolve().parents[1]
venues_path = pipeline_root / "data" / "crawled-data" / "venues.json"
output_file = pipeline_root / "artifacts" / "venues_detail.txt"
output_file.parent.mkdir(exist_ok=True)

with open(venues_path, 'r', encoding='utf-8') as f:
    venues = json.load(f)

with open(output_file, 'w', encoding='utf-8') as out:
    def log(msg=""):
        out.write(str(msg) + "\n")

    log(f"Total venues: {len(venues)}")
    
    log("\n--- First 5 venues (no lat/lon) ---")
    for v in venues[:5]:
        log(json.dumps(v, indent=2, ensure_ascii=False))

    log("\n--- First 5 venues WITH lat/lon (starts at index 18) ---")
    for v in venues[18:23]:
        log(json.dumps(v, indent=2, ensure_ascii=False))

    log("\n--- City distribution ---")
    city_counts = {}
    for v in venues:
        c = v.get('city')
        city_counts[c] = city_counts.get(c, 0) + 1
    for c, count in city_counts.items():
        log(f"  {c}: {count}")

    log("\n--- Sample addresses by city ---")
    venues_by_city = {}
    for v in venues:
        c = v.get('city')
        if c not in venues_by_city:
            venues_by_city[c] = []
        venues_by_city[c].append(v)

    for city, v_list in venues_by_city.items():
        log(f"\nCity: {city}")
        for v in v_list[:10]:
            log(f"  Name: {v['name']} | Address: {v['address']}")
