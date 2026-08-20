from unittest.mock import patch

import pytest

from app.tools.cost_abv_calculator import (
    RECIPE_COST_ABV_CALCULATION_VERSION,
    calculate_recipe_cost_and_abv,
)


def line(**overrides):
    values = {
        "display_name": "Gin",
        "normalized_ingredient_id": None,
        "amount": 45,
        "unit": "ml",
    }
    values.update(overrides)
    return values


PATCH_INGREDIENT = "app.tools.cost_abv_calculator.get_ingredient_by_name"
PATCH_PRICE = "app.tools.cost_abv_calculator.get_liquor_price_by_name_case_insensitive"


# ---------------------------------------------------------------------------
# Fully known recipe: existing per-ingredient math is preserved.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(PATCH_PRICE)
@patch(PATCH_INGREDIENT)
async def test_known_ingredients_compute_exact_totals(mock_get_ingredient, mock_get_price):
    mock_get_ingredient.side_effect = lambda name: (
        {"abv": 40.0} if "Vodka" in name else {"abv": 0.0}
    )
    mock_get_price.side_effect = lambda name: (
        [{"price_per_ml_vnd": 500.0}] if "Vodka" in name else [{"price_per_ml_vnd": 0.0}]
    )

    result = await calculate_recipe_cost_and_abv(
        [
            line(display_name="Absolut Vodka", amount=50, unit="ml"),
            line(display_name="Water", amount=150, unit="ml"),
        ]
    )

    assert result.calculation_version == RECIPE_COST_ABV_CALCULATION_VERSION
    assert result.total_volume_ml == 200.0
    assert result.estimated_cost_vnd == 25000.0
    assert result.estimated_abv == 10.0
    assert result.missing_data == []
    assert len(result.breakdown) == 2


@pytest.mark.asyncio
@patch(PATCH_PRICE)
@patch(PATCH_INGREDIENT)
async def test_case_and_whitespace_insensitive_lookup(mock_get_ingredient, mock_get_price):
    mock_get_ingredient.return_value = {"abv": 40.0}
    mock_get_price.return_value = [{"price_per_ml_vnd": 500.0}]

    result = await calculate_recipe_cost_and_abv(
        [line(display_name="  absolut vodka  ", amount=100, unit="ml")]
    )

    assert result.total_volume_ml == 100.0
    assert result.estimated_cost_vnd == 50000.0
    assert result.estimated_abv == 40.0
    assert result.missing_data == []


# ---------------------------------------------------------------------------
# No fabrication: missing ABV/price is excluded and reported, never zeroed.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(PATCH_PRICE)
@patch(PATCH_INGREDIENT)
async def test_missing_abv_nulls_estimated_abv_but_keeps_volume_and_cost(
    mock_get_ingredient, mock_get_price
):
    mock_get_ingredient.return_value = None  # ABV unknown
    mock_get_price.return_value = [{"price_per_ml_vnd": 500.0}]

    result = await calculate_recipe_cost_and_abv(
        [line(display_name="Mysterious Liquid X", amount=100, unit="ml")]
    )

    assert result.total_volume_ml == 100.0
    assert result.estimated_cost_vnd == 50000.0
    assert result.estimated_abv is None
    assert any("ABV unknown" in note for note in result.missing_data)
    assert result.breakdown[0].abv is None
    assert result.breakdown[0].abv_source == "unknown"


@pytest.mark.asyncio
@patch(PATCH_PRICE)
@patch(PATCH_INGREDIENT)
async def test_missing_price_nulls_estimated_cost_but_keeps_volume_and_abv(
    mock_get_ingredient, mock_get_price
):
    mock_get_ingredient.return_value = {"abv": 40.0}
    mock_get_price.return_value = []  # price unknown

    result = await calculate_recipe_cost_and_abv(
        [line(display_name="Rare Import Gin", amount=45, unit="ml")]
    )

    assert result.total_volume_ml == 45.0
    assert result.estimated_abv == 40.0
    assert result.estimated_cost_vnd is None
    assert any("price unknown" in note for note in result.missing_data)
    assert result.breakdown[0].cost_vnd is None
    assert result.breakdown[0].price_source == "unknown"


@pytest.mark.asyncio
@patch(PATCH_PRICE)
@patch(PATCH_INGREDIENT)
async def test_one_ingredient_missing_data_nulls_recipe_wide_aggregate(
    mock_get_ingredient, mock_get_price
):
    # A known ingredient plus one with unknown ABV: estimated_abv must not
    # silently understate the drink's real strength, so the whole aggregate
    # is null rather than a partial (misleading) ratio.
    mock_get_ingredient.side_effect = lambda name: {"abv": 40.0} if name == "Gin" else None
    mock_get_price.return_value = [{"price_per_ml_vnd": 100.0}]

    result = await calculate_recipe_cost_and_abv(
        [
            line(display_name="Gin", amount=45, unit="ml"),
            line(display_name="House Bitters Blend", amount=5, unit="ml"),
        ]
    )

    assert result.total_volume_ml == 50.0
    assert result.estimated_abv is None
    assert result.estimated_cost_vnd == 5000.0
    assert any("House Bitters Blend" in note and "ABV" in note for note in result.missing_data)


# ---------------------------------------------------------------------------
# Non-volume units (dash, drop, barspoon, piece): excluded from all totals.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("unit", ["dash", "drop", "barspoon", "piece"])
@pytest.mark.asyncio
@patch(PATCH_PRICE)
@patch(PATCH_INGREDIENT)
async def test_non_ml_units_are_excluded_from_totals_but_dont_block_known_ml_aggregate(
    mock_get_ingredient, mock_get_price, unit
):
    # A dash of bitters is a *structural* exclusion (no approved ml
    # conversion exists for it at all), not a data gap -- it must not null
    # out the ABV/cost computed from the ml-unit ingredients that ARE known.
    mock_get_ingredient.return_value = {"abv": 40.0}
    mock_get_price.return_value = [{"price_per_ml_vnd": 500.0}]

    result = await calculate_recipe_cost_and_abv(
        [
            line(display_name="Gin", amount=45, unit="ml"),
            line(display_name="Angostura Bitters", amount=2, unit=unit),
        ]
    )

    # The DB is never even queried for a non-volume-based line.
    bitters_call = [
        call for call in mock_get_ingredient.call_args_list if call.args[0] == "Angostura Bitters"
    ]
    assert bitters_call == []

    assert result.total_volume_ml == 45.0  # bitters excluded, not guessed
    assert result.estimated_abv == 40.0
    assert result.estimated_cost_vnd == 22500.0
    assert any("Angostura Bitters" in note and unit in note for note in result.missing_data)

    bitters_breakdown = next(b for b in result.breakdown if b.display_name == "Angostura Bitters")
    assert bitters_breakdown.volume_ml is None
    assert bitters_breakdown.unit == unit
    assert bitters_breakdown.abv_source == "unit_not_volume_based"
    assert bitters_breakdown.price_source == "unit_not_volume_based"


@pytest.mark.asyncio
async def test_recipe_entirely_non_ml_units_has_no_volume_totals():
    result = await calculate_recipe_cost_and_abv(
        [line(display_name="Bitters", amount=2, unit="dash")]
    )

    assert result.total_volume_ml is None
    assert result.estimated_abv is None
    assert result.estimated_cost_vnd is None
    assert any("no ingredients measured in ml" in note for note in result.missing_data)


# ---------------------------------------------------------------------------
# Zero/invalid totals.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_ingredient_list_returns_none_totals():
    result = await calculate_recipe_cost_and_abv([])

    assert result.total_volume_ml is None
    assert result.estimated_abv is None
    assert result.estimated_cost_vnd is None
    assert any("no ingredients supplied" in note for note in result.missing_data)
    assert result.breakdown == []


@pytest.mark.parametrize("bad_amount", [0, -5, "not a number", None])
@pytest.mark.asyncio
async def test_invalid_amount_is_excluded_and_reported_not_guessed(bad_amount):
    result = await calculate_recipe_cost_and_abv(
        [line(display_name="Gin", amount=bad_amount, unit="ml")]
    )

    assert result.total_volume_ml is None
    assert result.breakdown[0].volume_ml is None
    assert any("invalid amount" in note for note in result.missing_data)


@pytest.mark.asyncio
async def test_accepts_ingredient_line_pydantic_model_instances():
    from app.domain.schemas import IngredientLine

    result = await calculate_recipe_cost_and_abv(
        [IngredientLine(display_name="Soda Water", amount=60, unit="ml")]
    )

    assert result.total_volume_ml == 60.0
    assert result.breakdown[0].display_name == "Soda Water"


@pytest.mark.asyncio
async def test_as_dict_matches_recipe_version_field_names():
    result = await calculate_recipe_cost_and_abv([line(display_name="Soda Water", amount=60)])
    payload = result.as_dict()

    for key in ("total_volume_ml", "estimated_abv", "estimated_cost_vnd", "missing_data"):
        assert key in payload
