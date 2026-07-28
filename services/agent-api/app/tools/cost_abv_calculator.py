import logging
from typing import List, Dict, Any
from app.db.cache import get_ingredient_by_name, get_liquor_price_by_name_case_insensitive

logger = logging.getLogger(__name__)

async def calculate_cost_and_abv(ingredients_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate the total volume, total cost, pure alcohol volume, and final ABV 
    for a list of ingredients.
    
    Args:
        ingredients_list: A list of dicts, where each dict has:
            - "name": str (ingredient name)
            - "volume_ml": float/int (volume in milliliters)
            
    Returns:
        A dictionary containing:
            - "total_cost_vnd": float (total cost in VND)
            - "abv": float (final ABV percentage, e.g., 12.5)
            - "total_volume_ml": float (total volume in ml)
            - "breakdown": list of dicts with keys (name, volume_ml, cost, abv)
    """
    total_volume_ml = 0.0
    total_cost_vnd = 0.0
    total_pure_alcohol_ml = 0.0
    breakdown = []

    for item in ingredients_list:
        name = item.get("name", "").strip()
        volume_ml = float(item.get("volume_ml", 0.0))
        
        # 1. Query ABV from ingredients table (via cache)
        abv = 0.0
        try:
            ing_data = await get_ingredient_by_name(name)
            if ing_data:
                abv = float(ing_data.get("abv") or 0.0)
            else:
                logger.debug(f"Ingredient '{name}' not found in ingredients database. Defaulting ABV to 0.0.")
        except Exception as e:
            logger.error(f"Error querying ingredient '{name}' ABV: {e}")
            logger.debug(f"Defaulting ABV to 0.0 for ingredient '{name}'.")

        # 2. Query price from liquor_prices table (via cache)
        price_per_ml = 0.0
        try:
            price_data_list = await get_liquor_price_by_name_case_insensitive(name)
            if price_data_list:
                price_per_ml = float(price_data_list[0].get("price_per_ml_vnd", 0.0))
            else:
                logger.debug(f"Ingredient '{name}' not found in liquor prices database. Defaulting price to 0.0.")
        except Exception as e:
            logger.error(f"Error querying price for ingredient '{name}': {e}")
            logger.warning(f"Defaulting price to 0.0 for ingredient '{name}'.")

        # 3. Calculate metrics for this ingredient
        cost = volume_ml * price_per_ml
        pure_alcohol = volume_ml * (abv / 100.0)

        total_volume_ml += volume_ml
        total_cost_vnd += cost
        total_pure_alcohol_ml += pure_alcohol

        breakdown.append({
            "name": name,
            "volume_ml": volume_ml,
            "cost": cost,
            "abv": abv
        })

    # Calculate final ABV
    final_abv = 0.0
    if total_volume_ml > 0:
        final_abv = (total_pure_alcohol_ml / total_volume_ml) * 100.0

    return {
        "total_cost_vnd": total_cost_vnd,
        "abv": round(final_abv, 2),
        "total_volume_ml": total_volume_ml,
        "breakdown": breakdown
    }
