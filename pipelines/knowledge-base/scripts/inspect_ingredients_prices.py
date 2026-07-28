import json
import os
from pathlib import Path

pipeline_root = Path(__file__).resolve().parents[1]
data_dir = pipeline_root / "data" / "crawled-data"
output_file = pipeline_root / "artifacts" / "ingredients_prices_detail.txt"
output_file.parent.mkdir(exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as out:
    def log(msg=""):
        out.write(str(msg) + "\n")

    # Load files
    with open(os.path.join(data_dir, "thecocktaildb_ingredients.json"), 'r', encoding='utf-8') as f:
        ingredients = json.load(f)
    with open(os.path.join(data_dir, "liquor_prices.json"), 'r', encoding='utf-8') as f:
        prices = json.load(f)
    with open(os.path.join(data_dir, "thecocktaildb_cocktails.json"), 'r', encoding='utf-8') as f:
        cocktails = json.load(f)

    log(f"Ingredients count: {len(ingredients)}")
    log(f"Liquor prices count: {len(prices)}")
    log(f"Cocktails count: {len(cocktails)}")

    # Analyze ingredients strType
    log("\n--- Ingredients types (strType) ---")
    types = {}
    for ing in ingredients:
        t = ing.get('strType')
        types[t] = types.get(t, 0) + 1
    for t, count in types.items():
        log(f"  {t}: {count}")

    # Analyze prices categories
    log("\n--- Liquor prices categories ---")
    price_categories = {}
    for p in prices:
        cat = p.get('category')
        price_categories[cat] = price_categories.get(cat, 0) + 1
    for cat, count in price_categories.items():
        log(f"  {cat}: {count}")

    # Let's see some sample ingredients and prices
    log("\n--- Sample ingredients ---")
    for ing in ingredients[:15]:
        log(f"Name: {ing['strIngredient']} | Type: {ing.get('strType')} | Alcohol: {ing.get('strAlcohol')} | ABV: {ing.get('strABV')}")

    log("\n--- Sample liquor prices ---")
    for p in prices[:15]:
        log(f"Name: {p['name']} | Size: {p['size']} | Price: {p['price_vnd']} | Category: {p['category']}")

    # Check how many cocktail ingredients can be matched to base liquors
    log("\n--- Analyzing cocktail ingredients for base liquors ---")
    # Let's extract all unique ingredients used in cocktails
    all_cocktail_ingredients = set()
    for c in cocktails:
        for i in range(1, 16):
            ing_name = c.get(f'strIngredient{i}')
            if ing_name:
                all_cocktail_ingredients.add(ing_name.strip().lower())
    log(f"Unique ingredients in cocktails: {len(all_cocktail_ingredients)}")
    
    # Check match with thecocktaildb_ingredients.json
    ing_map = {ing['strIngredient'].lower(): ing for ing in ingredients}
    matched = 0
    unmatched = []
    for ci in all_cocktail_ingredients:
        if ci in ing_map:
            matched += 1
        else:
            unmatched.append(ci)
            
    log(f"Matched cocktail ingredients with ingredients.json: {matched} / {len(all_cocktail_ingredients)}")
    log(f"Sample unmatched cocktail ingredients (first 30): {unmatched[:30]}")
