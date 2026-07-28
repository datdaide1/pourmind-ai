import json
import os
from collections import Counter
from pathlib import Path

data_dir = Path(__file__).resolve().parents[1] / "data" / "crawled-data"
files = [
    "venues.json",
    "thecocktaildb_cocktails.json",
    "thecocktaildb_ingredients.json",
    "mixology_data.json",
    "liquor_prices.json"
]

def analyze_json_file(file_name):
    file_path = os.path.join(data_dir, file_name)
    print("=" * 80)
    print(f"Analyzing {file_name}...")
    print("=" * 80)
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"Error reading JSON: {e}")
            return
            
    print(f"Type: {type(data)}")
    if isinstance(data, list):
        print(f"Number of elements: {len(data)}")
        if len(data) == 0:
            return
        
        # Analyze keys and their types
        keys_counter = Counter()
        key_types = {}
        sample_values = {}
        null_counts = Counter()
        
        for item in data:
            if isinstance(item, dict):
                keys_counter.update(item.keys())
                for k, v in item.items():
                    if k not in key_types:
                        key_types[k] = set()
                    if v is not None:
                        key_types[k].add(type(v).__name__)
                    else:
                        null_counts[k] += 1
                        
                    # Save a sample value
                    if k not in sample_values and v is not None:
                        sample_values[k] = v
            else:
                print(f"Found non-dict element of type {type(item)}")
                
        print("\nFields found:")
        for key, count in keys_counter.items():
            types_str = ", ".join(key_types.get(key, ["NoneType"]))
            null_cnt = null_counts[key]
            sample = sample_values.get(key, "N/A")
            # Format sample if list/dict/long string
            if isinstance(sample, str) and len(sample) > 100:
                sample = sample[:97] + "..."
            elif isinstance(sample, (list, dict)):
                sample_str = str(sample)
                if len(sample_str) > 100:
                    sample = sample_str[:97] + "..."
            print(f"  - '{key}': type={types_str}, total={count}, null_count={null_cnt}, sample={sample}")
            
        print("\nSample Item:")
        print(json.dumps(data[0], indent=2, ensure_ascii=False)[:500])
        
    elif isinstance(data, dict):
        print(f"Keys: {list(data.keys())}")
        for k, v in data.items():
            print(f"Key: '{k}', type={type(v).__name__}")
            if isinstance(v, list):
                print(f"  Length of list: {len(v)}")
                if len(v) > 0:
                    print(f"  Sample: {v[0]}")
            elif isinstance(v, dict):
                print(f"  Keys: {list(v.keys())}")
                if len(v) > 0:
                    first_key = list(v.keys())[0]
                    print(f"  Sample for key '{first_key}': {v[first_key]}")

if __name__ == "__main__":
    for f in files:
        analyze_json_file(f)
