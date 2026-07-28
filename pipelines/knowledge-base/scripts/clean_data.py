import os
import json
import re
import unicodedata
import hashlib
from pathlib import Path

# Paths
PIPELINE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PIPELINE_ROOT / "data" / "crawled-data"
OUTPUT_DIR = PIPELINE_ROOT / "data" / "cleaned"

def normalize_string(s: str) -> str:
    if not isinstance(s, str):
        return s
    # Standardize to Unicode NFC normalization form
    s = unicodedata.normalize('NFC', s)
    # Normalize whitespaces: remove double spaces/newlines
    s = " ".join(s.split())
    return s

def slugify(text: str) -> str:
    text = text.lower()
    # Remove Vietnamese accents/diacritics
    diacritics = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'đ': 'd'
    }
    for char, replacement in diacritics.items():
        text = text.replace(char, replacement)
    
    # Standardize via NFKD to catch any remaining diacritics
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def generate_venue_id(name: str, city: str, address: str) -> str:
    addr_hash = hashlib.md5(address.lower().encode('utf-8')).hexdigest()[:6]
    return f"{slugify(name)}-{addr_hash}-{slugify(city)}"

def extract_district(address: str, city: str) -> str:
    address_lower = address.lower()
    city_lower = city.lower()
    
    if "ho chi minh" in city_lower or "hcmc" in city_lower:
        if "district 1" in address_lower or "quận 1" in address_lower or "q1" in address_lower:
            return "District 1"
        if "district 3" in address_lower or "quận 3" in address_lower or "q3" in address_lower:
            return "District 3"
        if "binh thanh" in address_lower or "bình thạnh" in address_lower:
            return "Binh Thanh District"
        if "district 2" in address_lower or "quận 2" in address_lower or "thu duc" in address_lower or "thủ đức" in address_lower:
            return "Thu Duc District"
        # Street matching
        if any(street in address_lower for street in ["nguyen hue", "nguyễn huệ", "pasteur", "nguyen thiep", "nguyễn thiệp", "ton that dam", "tôn thất đạm", "le loi", "lê lợi", "le duan", "lê duẩn", "hai ba trung", "hai bà trưng", "dong khoi", "đồng khởi", "mac thi buoi", "mạc thị bưởi"]):
            return "District 1"
        if "pham viet chanh" in address_lower or "phạm viết chánh" in address_lower:
            return "Binh Thanh District"
        return "District 1" # Default
        
    elif "hanoi" in city_lower or "hà nội" in city_lower:
        if "hoan kiem" in address_lower or "hoàn kiếm" in address_lower:
            return "Hoan Kiem District"
        if "ba dinh" in address_lower or "ba đình" in address_lower:
            return "Ba Dinh District"
        if "tay ho" in address_lower or "tây hồ" in address_lower:
            return "Tay Ho District"
        # Ward/street matching
        if any(ward in address_lower for ward in ["hang buom", "hàng buồm", "hang bac", "hàng bạc", "hang ma", "hàng mã", "hang bo", "hàng bồ", "hang bong", "hàng bông", "ta hien", "tạ hiện", "hang be", "hàng bè", "phung hung", "phùng hưng", "tong duy tan", "tống duy tân", "tran hung dao", "trần hưng đạo"]):
            return "Hoan Kiem District"
        if "pasteur" in address_lower:
            return "Hai Ba Trung District"
        if "nguyen hue" in address_lower or "nguyễn huệ" in address_lower:
            return "Ha Dong District"
        return "Hoan Kiem District" # Default
        
    elif "da nang" in city_lower or "đà nẵng" in city_lower:
        if "hai chau" in address_lower or "hải châu" in address_lower:
            return "Hai Chau District"
        if "son tra" in address_lower or "sơn trà" in address_lower:
            return "Son Tra District"
        if "thanh khe" in address_lower or "thanh khê" in address_lower:
            return "Thanh Khe District"
        # Street matching
        if any(street in address_lower for street in ["nguyen chi thanh", "nguyễn chí thanh", "bach dang", "bạch đằng", "phuoc ninh", "phước ninh", "pasteur"]):
            return "Hai Chau District"
        if "hai ba trung" in address_lower or "hai bà trưng" in address_lower:
            return "Thanh Khe District"
        return "Hai Chau District" # Default
        
    elif "nha trang" in city_lower:
        if "pasteur" in address_lower or "le loi" in address_lower or "le duan" in address_lower or "hai ba trung" in address_lower:
            return "Loc Tho Ward"
        return "Nha Trang City"
        
    elif "hai phong" in city_lower or "hải phòng" in city_lower:
        if "hong bang" in address_lower or "hồng bàng" in address_lower:
            return "Hong Bang District"
        if "ngo quyen" in address_lower or "ngô quyền" in address_lower:
            return "Ngo Quyen District"
        if "le chan" in address_lower or "lê chân" in address_lower:
            return "Le Chan District"
        if "pasteur" in address_lower or "le duan" in address_lower or "bach dang" in address_lower or "le loi" in address_lower or "nguyen hue" in address_lower:
            return "Hong Bang District"
        return "Hong Bang District"
        
    elif "vung tau" in city_lower or "vũng tàu" in city_lower:
        if "le duan" in address_lower or "le loi" in address_lower or "bach dang" in address_lower or "tran hung dao" in address_lower or "hai ba trung" in address_lower:
            return "Ward 1"
        return "Vung Tau City"
        
    return "Unknown"

# Base Liquor classification maps
INGREDIENT_TO_BASE = {
    "applejack": "Brandy",
    "cachaca": "Rum",
    "cachaça": "Rum",
    "pisco": "Brandy",
    "scotch": "Whiskey",
    "rye": "Whiskey",
    "bourbon": "Bourbon",
    "campari": "Liqueur",
    "schnapps": "Liqueur",
    "irish cream": "Liqueur",
    "baileys": "Liqueur",
    "kahlua": "Liqueur",
    "triple sec": "Liqueur",
    "cointreau": "Liqueur",
    "grand marnier": "Liqueur",
    "blue curacao": "Liqueur",
    "orange curacao": "Liqueur",
    "amaretto": "Liqueur",
    "frangelico": "Liqueur",
    "kahlúa": "Liqueur",
    "vermouth": "Liqueur",
    "lillet": "Liqueur",
    "dubonnet": "Liqueur",
    "absinthe": "Liqueur",
    "galliano": "Liqueur",
    "chartreuse": "Liqueur",
    "drambuie": "Liqueur",
    "benedictine": "Liqueur",
    "liqueur": "Liqueur",
    "liquer": "Liqueur",
    "sambuca": "Liqueur",
    "ricard": "Liqueur",
    "southern comfort": "Liqueur",
    "firewater": "Liqueur",
    "hot damn": "Liqueur",
    "everclear": "Spirit",
    "grain alcohol": "Spirit",
    "champagne": "Wine",
    "prosecco": "Wine",
    "sherry": "Wine",
    "port": "Wine",
    "red wine": "Wine",
    "white wine": "Wine",
    "rose": "Wine",
    "rosé": "Wine",
    "beer": "Beer",
    "lager": "Beer",
    "guinness": "Beer",
    "stout": "Beer",
    "ale": "Beer",
    "cider": "Cider",
    "sake": "Sake",
    "cognac": "Cognac",
    "brandy": "Brandy",
    "gin": "Gin",
    "rum": "Rum",
    "vodka": "Vodka",
    "absolut": "Vodka",
    "tequila": "Tequila",
    "whiskey": "Whiskey",
    "whisky": "Whiskey"
}

TYPE_TO_BASE = {
    "liqueur": "Liqueur",
    "liquer": "Liqueur",
    "schnapps": "Liqueur",
    "whiskey": "Whiskey",
    "whisky": "Whiskey",
    "rum": "Rum",
    "vodka": "Vodka",
    "gin": "Gin",
    "tequila": "Tequila",
    "brandy": "Brandy",
    "cognac": "Cognac",
    "wine": "Wine",
    "fortified wine": "Wine",
    "beer": "Beer",
    "cider": "Cider",
    "spirit": "Spirit"
}

def detect_base_liquor(drink, ingredients_db) -> str:
    alcoholic_type = drink.get("strAlcoholic", "").strip().lower()
    if alcoholic_type == "non alcoholic":
        return "None"
        
    drink_ings = []
    for i in range(1, 16):
        ing = drink.get(f"strIngredient{i}")
        if ing:
            drink_ings.append(normalize_string(ing).lower())
            
    if not drink_ings:
        return "Other"
        
    # First pass: check first ingredient (primary)
    first_ing = drink_ings[0]
    for key, base in INGREDIENT_TO_BASE.items():
        if key in first_ing:
            return base
            
    # Second pass: check all ingredients
    for ing in drink_ings:
        for key, base in INGREDIENT_TO_BASE.items():
            if key in ing:
                return base
                
    # Third pass: lookup types in ingredients DB
    ing_lookup = {normalize_string(ing["strIngredient"]).lower(): ing for ing in ingredients_db}
    for ing in drink_ings:
        ing_info = ing_lookup.get(ing)
        if ing_info:
            ing_type = ing_info.get("strType")
            if ing_type:
                ing_type_lower = normalize_string(ing_type).lower()
                for key, base in TYPE_TO_BASE.items():
                    if key in ing_type_lower:
                        return base

    return "Other"

def parse_size_ml(size_str: str) -> int:
    size_str = size_str.lower().strip()
    match = re.search(r"(\d+)\s*(ml|l)", size_str)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit == "l":
            return val * 1000
        return val
    return 700 # Default if unparseable

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Clean venues.json
    venues_path = os.path.join(DATA_DIR, "venues.json")
    with open(venues_path, "r", encoding="utf-8") as f:
        raw_venues = json.load(f)
        
    ratings = [v['rating'] for v in raw_venues if v.get('rating') is not None]
    default_rating = round(sum(ratings) / len(ratings), 2) if ratings else 4.4
    
    cleaned_venues = []
    for v in raw_venues:
        name = normalize_string(v["name"])
        city = normalize_string(v["city"])
        address = normalize_string(v["address"])
        vibe = normalize_string(v.get("vibe", ""))
        
        rating_raw = v.get("rating")
        rating_val = float(rating_raw) if rating_raw is not None else default_rating
        
        reviews = []
        if vibe:
            reviews.append(f"Atmosphere: {vibe}")
            
        cleaned_venues.append({
            "id": generate_venue_id(name, city, address),
            "name": name,
            "city": city,
            "district": extract_district(address, city),
            "address": address,
            "rating": rating_val,
            "reviews": reviews
        })
        
    venues_out = os.path.join(OUTPUT_DIR, "venues.json")
    with open(venues_out, "w", encoding="utf-8") as f:
        json.dump(cleaned_venues, f, indent=2, ensure_ascii=False)
    print(f"Cleaned venues: {len(cleaned_venues)} saved to {venues_out}")
    
    # 2. Clean liquor_prices.json
    prices_path = os.path.join(DATA_DIR, "liquor_prices.json")
    with open(prices_path, "r", encoding="utf-8") as f:
        raw_prices = json.load(f)
        
    cleaned_prices = []
    category_prices = {} # category -> list of (price_vnd, size_ml)
    
    for p in raw_prices:
        name = normalize_string(p["name"])
        category = normalize_string(p["category"])
        size_raw = normalize_string(p["size"])
        
        # Merge Whisky & Whiskey
        if category.lower() in ["whisky", "whiskey"]:
            category = "Whiskey"
            
        size_ml = parse_size_ml(size_raw)
        price_vnd = int(p["price_vnd"])
        price_per_ml = price_vnd / size_ml if size_ml > 0 else 0.0
        
        cleaned_prices.append({
            "name": name,
            "category": category,
            "size_raw": size_raw,
            "size_ml": size_ml,
            "price_vnd": price_vnd,
            "price_per_ml_vnd": round(price_per_ml, 4)
        })
        
        if category not in category_prices:
            category_prices[category] = []
        category_prices[category].append(price_per_ml)
        
    prices_out = os.path.join(OUTPUT_DIR, "liquor_prices.json")
    with open(prices_out, "w", encoding="utf-8") as f:
        json.dump(cleaned_prices, f, indent=2, ensure_ascii=False)
    print(f"Cleaned liquor prices: {len(cleaned_prices)} saved to {prices_out}")
    
    # Compute average price per ml for categories
    category_avg_price_per_ml = {}
    for cat, ml_prices in category_prices.items():
        category_avg_price_per_ml[cat] = sum(ml_prices) / len(ml_prices)
    
    # 3. Clean mixology_data.json
    mixology_path = os.path.join(DATA_DIR, "mixology_data.json")
    with open(mixology_path, "r", encoding="utf-8") as f:
        raw_mixology = json.load(f)
        
    cleaned_substitutions = []
    for item in raw_mixology.get("substitutions", []):
        ingredient = normalize_string(item["ingredient"])
        raw_subs = item.get("substitutes", [])
        
        # Clean each substitute and remove empty elements
        substitutes = [normalize_string(sub) for sub in raw_subs if sub]
        notes = normalize_string(item.get("notes", ""))
        
        # Deduplicate substitutes while preserving order
        seen = set()
        deduped_subs = []
        for sub in substitutes:
            if sub.lower() not in seen:
                seen.add(sub.lower())
                deduped_subs.append(sub)
                
        cleaned_substitutions.append({
            "ingredient": ingredient,
            "substitutes": deduped_subs,
            "notes": notes
        })
        
    cleaned_mixology = {
        "metadata": {
            "version": normalize_string(raw_mixology.get("metadata", {}).get("version", "1.0")),
            "description": normalize_string(raw_mixology.get("metadata", {}).get("description", "")),
            "usage": normalize_string(raw_mixology.get("metadata", {}).get("usage", ""))
        },
        "substitutions": cleaned_substitutions
    }
    mixology_out = os.path.join(OUTPUT_DIR, "mixology_data.json")
    with open(mixology_out, "w", encoding="utf-8") as f:
        json.dump(cleaned_mixology, f, indent=2, ensure_ascii=False)
    print(f"Cleaned mixology matrix saved to {mixology_out}")
    
    # 4. Clean ingredients.json
    ingredients_path = os.path.join(DATA_DIR, "thecocktaildb_ingredients.json")
    with open(ingredients_path, "r", encoding="utf-8") as f:
        raw_ingredients = json.load(f)
        
    cleaned_ingredients = []
    for ing in raw_ingredients:
        ing_id = str(ing["idIngredient"]).strip()
        name = normalize_string(ing["strIngredient"])
        desc = normalize_string(ing.get("strDescription") or "")
        ing_type = normalize_string(ing.get("strType") or "")
        
        is_alc = ing.get("strAlcohol") == "Yes"
        # Everclear correction
        if name.lower() == "everclear":
            is_alc = True
            
        abv = None
        str_abv = ing.get("strABV")
        if str_abv:
            try:
                abv = float(str_abv)
            except ValueError:
                pass
        if name.lower() == "everclear" and abv is None:
            abv = 95.0
            
        cleaned_ingredients.append({
            "id": ing_id,
            "name": name,
            "description": desc if desc else None,
            "type": ing_type if ing_type else None,
            "is_alcoholic": is_alc,
            "abv": abv
        })
        
    ingredients_out = os.path.join(OUTPUT_DIR, "ingredients.json")
    with open(ingredients_out, "w", encoding="utf-8") as f:
        json.dump(cleaned_ingredients, f, indent=2, ensure_ascii=False)
    print(f"Cleaned ingredients: {len(cleaned_ingredients)} saved to {ingredients_out}")
    
    # 5. Clean thecocktaildb_cocktails.json
    cocktails_path = os.path.join(DATA_DIR, "thecocktaildb_cocktails.json")
    with open(cocktails_path, "r", encoding="utf-8") as f:
        raw_cocktails = json.load(f)
        
    cleaned_cocktails = []
    for c in raw_cocktails:
        drink_id = str(c["idDrink"]).strip()
        name = normalize_string(c["strDrink"])
        alcoholic_type = normalize_string(c.get("strAlcoholic", "Alcoholic"))
        
        base_liquor = detect_base_liquor(c, raw_ingredients)
        
        # Extract ingredients list
        ingredients_list = []
        for i in range(1, 16):
            ing = c.get(f"strIngredient{i}")
            if ing:
                ing_cleaned = normalize_string(ing)
                if ing_cleaned:
                    ingredients_list.append(ing_cleaned)
                    
        instructions = normalize_string(c.get("strInstructions", ""))
        
        # Estimate Price
        is_alcoholic = alcoholic_type.lower() != "non alcoholic"
        if not is_alcoholic:
            price = 50000
        else:
            # Look up base liquor in average price mapping
            avg_price_ml = category_avg_price_per_ml.get(base_liquor)
            if avg_price_ml is not None:
                # 45ml shot with 4.0x markup
                raw_price = 45 * avg_price_ml * 4.0
                price = int(round(raw_price / 10000) * 10000)
                if price < 50000:
                    price = 120000
            else:
                price = 120000 # Flat price fallback
                
        cleaned_cocktails.append({
            "id": drink_id,
            "name": name,
            "alcoholic_type": alcoholic_type,
            "base_liquor": base_liquor,
            "ingredients": ingredients_list,
            "instructions": instructions,
            "price": price
        })
        
    cocktails_out = os.path.join(OUTPUT_DIR, "cocktails.json")
    with open(cocktails_out, "w", encoding="utf-8") as f:
        json.dump(cleaned_cocktails, f, indent=2, ensure_ascii=False)
    print(f"Cleaned cocktails: {len(cleaned_cocktails)} saved to {cocktails_out}")

if __name__ == "__main__":
    main()
