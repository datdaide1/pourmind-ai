import logging
from typing import Dict, Any
from app.db.cache import get_mixology_rule_by_ingredient_case_insensitive

logger = logging.getLogger(__name__)

async def get_ingredient_substitutes(ingredient_name: str) -> Dict[str, Any]:
    """
    Look up substitutes for an ingredient in the mixology rules database case-insensitively.
    
    Args:
        ingredient_name: The name of the ingredient to substitute.
        
    Returns:
        A dictionary containing:
            - "substitutes": list of strings (alternative ingredients)
            - "notes": string (mixology notes or explanation)
            - "message": string (optional message if not found)
    """
    try:
        rule = await get_mixology_rule_by_ingredient_case_insensitive(ingredient_name)
        if rule:
            return {
                "substitutes": rule.get("substitutes") or [],
                "notes": rule.get("notes") or ""
            }
    except Exception as e:
        logger.error(f"Error querying mixology rule for '{ingredient_name}': {e}")

    # No rule found or exception occurred
    msg = "No substitutes found in the mixology rules database."
    return {
        "substitutes": [],
        "notes": msg,
        "message": msg
    }
