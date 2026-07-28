import os
import json
import re
import hashlib
from pathlib import Path

pipeline_root = Path(__file__).resolve().parents[1]
venues_path = pipeline_root / "data" / "crawled-data" / "venues.json"
output_file = pipeline_root / "artifacts" / "test_cleaning_output.txt"
output_file.parent.mkdir(exist_ok=True)

def slugify(text: str) -> str:
    text = text.lower()
    # Remove Vietnamese accents/diacritics
    # Simple replacement dictionary for common accents
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
    
    # Remove non-alphanumeric characters, replace with hyphens
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
        
    return "Unknown District"

with open(venues_path, 'r', encoding='utf-8') as f:
    venues = json.load(f)

# Calculate default rating (overall average of non-null ratings)
ratings = [v['rating'] for v in venues if v.get('rating') is not None]
default_rating = round(sum(ratings) / len(ratings), 2) if ratings else 4.4

cleaned_venues = []
for v in venues[:30]:
    raw_rating = v.get('rating')
    rating_val = float(raw_rating) if raw_rating is not None else default_rating
    
    cleaned = {
        "id": generate_venue_id(v['name'], v['city'], v['address']),
        "name": v['name'],
        "city": v['city'],
        "district": extract_district(v['address'], v['city']),
        "address": v['address'],
        "rating": rating_val,
        "reviews": [] # Empty list as target schema requires reviews array
    }
    cleaned_venues.append(cleaned)

with open(output_file, 'w', encoding='utf-8') as out:
    out.write(json.dumps(cleaned_venues, indent=2, ensure_ascii=False))
    print(f"Cleaned {len(cleaned_venues)} venues successfully and wrote to {output_file}")
