import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence

from app.db.cache import get_ingredient_by_name, get_liquor_price_by_name_case_insensitive

logger = logging.getLogger(__name__)

# Bumped whenever the recipe-cost-abv formula or field semantics change, so
# callers/UI can tell which rules produced a given RecipeVersion's numbers.
RECIPE_COST_ABV_CALCULATION_VERSION = "recipe-cost-abv-v1"

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


# ---------------------------------------------------------------------------
# RCP-02: normalized-recipe-contract calculator.
#
# `calculate_cost_and_abv` above is the legacy chat-agent tool (app/agents/
# nodes.py `calculate_cost_tool`): it takes pre-normalized {"name",
# "volume_ml"} pairs and silently defaults an unknown ABV/price to 0.0. It is
# intentionally left untouched so the existing agent behavior is unaffected.
#
# `calculate_recipe_cost_and_abv` below is the new entry point for the
# regular-guest-intelligence recipe pipeline (RCP-01 -> RCP-02 -> RCP-03). It
# accepts RCP-01-normalized ingredient lines (mixed units: ml, dash, drop,
# barspoon, piece) and NEVER fabricates a price or ABV: any ingredient whose
# unit has no safe volume conversion, or whose ABV/price is unknown, is
# excluded from the corresponding total and reported in `missing_data`
# instead of being defaulted to 0.
# ---------------------------------------------------------------------------

# Only ingredients measured in this unit have a well-defined volume; dash,
# drop, barspoon and piece have no approved ml conversion (see RCP-01), so
# they can never contribute to total_volume_ml, estimated_abv or
# estimated_cost_vnd.
_VOLUME_UNIT = "ml"


@dataclass(frozen=True)
class IngredientCostAbvBreakdown:
    """Per-ingredient detail behind the recipe totals, for UI/debugging."""

    display_name: str
    normalized_ingredient_id: str | None
    amount: float
    unit: str
    volume_ml: float | None
    abv: float | None
    abv_source: str  # "ingredients_table" | "unit_not_volume_based" | "unknown"
    price_per_ml_vnd: float | None
    price_source: str  # "liquor_prices_table" | "unit_not_volume_based" | "unknown"
    pure_alcohol_ml: float | None
    cost_vnd: float | None


@dataclass(frozen=True)
class RecipeCostAbvResult:
    """Matches the FND-02 RecipeVersion/RecipeSnapshot numeric contract."""

    calculation_version: str
    total_volume_ml: float | None
    estimated_abv: float | None
    estimated_cost_vnd: float | None
    missing_data: list[str] = field(default_factory=list)
    breakdown: list[IngredientCostAbvBreakdown] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        """Plain-dict view, e.g. for spreading into a RecipeVersion payload."""
        return {
            "calculation_version": self.calculation_version,
            "total_volume_ml": self.total_volume_ml,
            "estimated_abv": self.estimated_abv,
            "estimated_cost_vnd": self.estimated_cost_vnd,
            "missing_data": list(self.missing_data),
            "breakdown": [vars(item) for item in self.breakdown],
        }


def _extract_ingredient_fields(
    item: "Mapping[str, Any]",
) -> tuple[str, str | None, Any, str]:
    """Read display_name/normalized_ingredient_id/amount/unit off a mapping.

    Accepts anything shaped like an `IngredientLine` (a Pydantic model dump,
    a plain dict, or the model instance itself via `dict(item)`/attribute
    access), so callers can pass RCP-01 output directly.
    """
    getter = item.get if isinstance(item, Mapping) else lambda k: getattr(item, k, None)
    display_name = str(getter("display_name") or "").strip()
    normalized_ingredient_id = getter("normalized_ingredient_id")
    amount = getter("amount")
    unit = str(getter("unit") or "").strip().lower()
    return display_name, normalized_ingredient_id, amount, unit


async def calculate_recipe_cost_and_abv(
    ingredients: Sequence[Mapping[str, Any]],
) -> RecipeCostAbvResult:
    """Compute best-effort, never-fabricated cost/ABV totals for a recipe.

    Args:
        ingredients: RCP-01-normalized ingredient lines, each shaped like
            `IngredientLine` (display_name, normalized_ingredient_id, amount,
            unit in {ml, dash, drop, barspoon, piece}).

    Returns:
        A `RecipeCostAbvResult`. `total_volume_ml` always sums only the
        ml-unit ingredients (dash/drop/barspoon/piece have no approved
        conversion and are structurally excluded). `estimated_abv` and
        `estimated_cost_vnd` are computed from that same ml-unit set, but
        only when *every* ml-unit ingredient's ABV/price is actually known:
        a single unknown component would otherwise silently understate the
        aggregate rather than being visibly missing, so the aggregate is
        `None` instead. Every excluded or unknown ingredient (non-ml unit,
        unknown ABV, unknown price, invalid amount) is named in
        `missing_data` either way, so a caller never has to guess why a
        total is partial or absent.
    """
    breakdown: List[IngredientCostAbvBreakdown] = []
    missing_data: List[str] = []

    known_volume_ml = 0.0
    known_pure_alcohol_ml = 0.0
    abv_complete = True
    known_cost_vnd = 0.0
    cost_complete = True
    any_volume_line = False

    for raw in ingredients:
        display_name, normalized_ingredient_id, raw_amount, unit = _extract_ingredient_fields(raw)

        try:
            amount = float(raw_amount)
        except (TypeError, ValueError):
            amount = None
        if not display_name or amount is None or amount <= 0:
            missing_data.append(
                f"{display_name or '(unnamed ingredient)'}: invalid amount {raw_amount!r}, excluded from totals"
            )
            breakdown.append(
                IngredientCostAbvBreakdown(
                    display_name=display_name,
                    normalized_ingredient_id=normalized_ingredient_id,
                    amount=0.0,
                    unit=unit,
                    volume_ml=None,
                    abv=None,
                    abv_source="unknown",
                    price_per_ml_vnd=None,
                    price_source="unknown",
                    pure_alcohol_ml=None,
                    cost_vnd=None,
                )
            )
            abv_complete = False
            cost_complete = False
            continue

        if unit != _VOLUME_UNIT:
            # Structural exclusion, not a data gap: dash/drop/barspoon/piece
            # have no approved ml conversion (RCP-01), so this line can never
            # contribute to the volume-based totals. It is reported below,
            # but it does not block computing ABV/cost from the ml-based
            # ingredients that *are* known -- almost every recipe has a dash
            # of something, and that alone should not null the whole recipe.
            missing_data.append(
                f"{display_name} ({amount:g} {unit}): unit has no approved volume conversion, "
                "excluded from total_volume_ml/estimated_abv/estimated_cost_vnd"
            )
            breakdown.append(
                IngredientCostAbvBreakdown(
                    display_name=display_name,
                    normalized_ingredient_id=normalized_ingredient_id,
                    amount=amount,
                    unit=unit,
                    volume_ml=None,
                    abv=None,
                    abv_source="unit_not_volume_based",
                    price_per_ml_vnd=None,
                    price_source="unit_not_volume_based",
                    pure_alcohol_ml=None,
                    cost_vnd=None,
                )
            )
            continue

        any_volume_line = True
        volume_ml = amount
        known_volume_ml += volume_ml

        abv: float | None = None
        abv_source = "unknown"
        try:
            ing_data = await get_ingredient_by_name(display_name)
        except Exception as exc:  # pragma: no cover - defensive, mirrors legacy tool
            logger.error(f"Error querying ingredient '{display_name}' ABV: {exc}")
            ing_data = None
        if ing_data is not None and ing_data.get("abv") is not None:
            abv = float(ing_data["abv"])
            abv_source = "ingredients_table"
        else:
            missing_data.append(f"{display_name}: ABV unknown, excluded from estimated_abv")
            abv_complete = False

        price_per_ml: float | None = None
        price_source = "unknown"
        try:
            price_rows = await get_liquor_price_by_name_case_insensitive(display_name)
        except Exception as exc:  # pragma: no cover - defensive, mirrors legacy tool
            logger.error(f"Error querying price for ingredient '{display_name}': {exc}")
            price_rows = None
        if price_rows:
            price_per_ml = float(price_rows[0].get("price_per_ml_vnd", 0.0))
            price_source = "liquor_prices_table"
        else:
            missing_data.append(f"{display_name}: price unknown, excluded from estimated_cost_vnd")
            cost_complete = False

        pure_alcohol_ml = volume_ml * (abv / 100.0) if abv is not None else None
        cost_vnd = volume_ml * price_per_ml if price_per_ml is not None else None

        if pure_alcohol_ml is not None:
            known_pure_alcohol_ml += pure_alcohol_ml
        if cost_vnd is not None:
            known_cost_vnd += cost_vnd

        breakdown.append(
            IngredientCostAbvBreakdown(
                display_name=display_name,
                normalized_ingredient_id=normalized_ingredient_id,
                amount=amount,
                unit=unit,
                volume_ml=volume_ml,
                abv=abv,
                abv_source=abv_source,
                price_per_ml_vnd=price_per_ml,
                price_source=price_source,
                pure_alcohol_ml=pure_alcohol_ml,
                cost_vnd=cost_vnd,
            )
        )

    if not any_volume_line:
        if not ingredients:
            missing_data.append("no ingredients supplied, totals unavailable")
        else:
            missing_data.append(
                "no ingredients measured in ml, total_volume_ml/estimated_abv/estimated_cost_vnd unavailable"
            )
        return RecipeCostAbvResult(
            calculation_version=RECIPE_COST_ABV_CALCULATION_VERSION,
            total_volume_ml=None,
            estimated_abv=None,
            estimated_cost_vnd=None,
            missing_data=missing_data,
            breakdown=breakdown,
        )

    estimated_abv = (
        round((known_pure_alcohol_ml / known_volume_ml) * 100.0, 2) if abv_complete else None
    )
    estimated_cost_vnd = round(known_cost_vnd, 2) if cost_complete else None

    return RecipeCostAbvResult(
        calculation_version=RECIPE_COST_ABV_CALCULATION_VERSION,
        total_volume_ml=round(known_volume_ml, 2),
        estimated_abv=estimated_abv,
        estimated_cost_vnd=estimated_cost_vnd,
        missing_data=missing_data,
        breakdown=breakdown,
    )
