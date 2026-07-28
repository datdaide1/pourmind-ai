import json
import os
from pathlib import Path

pipeline_root = Path(__file__).resolve().parents[1]
data_dir = pipeline_root / "data" / "crawled-data"
output_file = pipeline_root / "artifacts" / "find_reviews_output.txt"
output_file.parent.mkdir(exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as out:
    def log(msg=""):
        out.write(str(msg) + "\n")

    # Check keys in golden_scenarios.json
    gs_path = os.path.join(data_dir, "golden_scenarios.json")
    if os.path.exists(gs_path):
        log("Analyzing golden_scenarios.json...")
        with open(gs_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                log(f"Type: {type(data)}")
                if isinstance(data, list):
                    log(f"Count: {len(data)}")
                    if len(data) > 0:
                        log(f"Sample item keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
                        log("Sample item:")
                        log(json.dumps(data[0], indent=2)[:500])
                elif isinstance(data, dict):
                    log(f"Keys: {list(data.keys())}")
                    for k, v in data.items():
                        log(f"Key '{k}': type={type(v).__name__}")
                        if isinstance(v, list) and len(v) > 0:
                            log(f"  Sample list item keys: {list(v[0].keys()) if isinstance(v[0], dict) else type(v[0])}")
            except Exception as e:
                log(f"Error: {e}")

    # Let's inspect venues.json in detail
    venues_path = os.path.join(data_dir, "venues.json")
    if os.path.exists(venues_path):
        with open(venues_path, 'r', encoding='utf-8') as f:
            venues = json.load(f)
        log("\nVenues detailed stats:")
        cities = set(v.get('city') for v in venues)
        log(f"Unique cities: {cities}")
        vibes = set(v.get('vibe') for v in venues)
        log(f"Unique vibes count: {len(vibes)}")
        log(f"Sample vibes: {list(vibes)[:10]}")
        
        log("\nSample addresses from venues.json:")
        for v in venues[:20]:
            log(f"Name: {v['name']} | City: {v['city']} | Address: {v['address']}")
            
        log("\nAnalyzing missing lat/lon:")
        missing_latlon = [v for v in venues if v.get('lat') is None or v.get('lon') is None]
        log(f"Number of venues missing lat/lon: {len(missing_latlon)}")
        for v in missing_latlon:
            log(f"  Missing lat/lon: {v['name']} in {v['city']} ({v['address']})")
