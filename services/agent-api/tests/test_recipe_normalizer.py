import pytest

from app.tools.recipe_normalizer import (
    IngredientRegistry,
    RawIngredientLine,
    normalize_recipe_ingredients,
    resolve_unit,
)


def raw(**overrides):
    values = {"display_name": "Gin", "amount": 45, "unit": "ml"}
    values.update(overrides)
    return RawIngredientLine(**values)


# ---------------------------------------------------------------------------
# Units: all five supported units, plus common spelling/casing aliases.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_unit", "expected"),
    [
        ("ml", "ml"),
        ("ML", "ml"),
        ("  ml  ", "ml"),
        ("milliliters", "ml"),
        ("dash", "dash"),
        ("Dashes", "dash"),
        ("drop", "drop"),
        ("Drops", "drop"),
        ("barspoon", "barspoon"),
        ("bar spoon", "barspoon"),
        ("bsp", "barspoon"),
        ("piece", "piece"),
        ("Pieces", "piece"),
        ("pcs", "piece"),
    ],
)
def test_resolve_unit_accepts_approved_aliases(raw_unit, expected):
    assert resolve_unit(raw_unit) == expected


@pytest.mark.parametrize("raw_unit", ["oz", "ounce", "tsp", "cl", "cup", "", "   ", None])
def test_resolve_unit_rejects_units_without_an_approved_rule(raw_unit):
    assert resolve_unit(raw_unit) is None


@pytest.mark.parametrize("unit", ["ml", "dash", "drop", "barspoon", "piece"])
def test_normalize_accepts_all_five_supported_units(unit):
    result = normalize_recipe_ingredients([raw(unit=unit)])
    assert result.unresolved == []
    assert len(result.ingredients) == 1
    assert result.ingredients[0].unit == unit


def test_normalize_reports_unsupported_unit_as_unresolved_not_guessed():
    result = normalize_recipe_ingredients([raw(unit="oz")])
    assert result.ingredients == []
    assert len(result.unresolved) == 1
    assert result.unresolved[0].reason == "unrecognized_unit"
    assert result.unresolved[0].raw_unit == "oz"
    assert any("oz" in note for note in result.missing_data)


# ---------------------------------------------------------------------------
# Amounts: decimals, fractions, and invalid/out-of-range values.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_amount", "expected"),
    [
        (45, 45.0),
        (0.5, 0.5),
        ("30", 30.0),
        ("22.5", 22.5),
        ("1/2", 0.5),
        ("3/4", 0.75),
        ("1 1/2", 1.5),
    ],
)
def test_normalize_parses_decimal_and_fraction_amounts(raw_amount, expected):
    result = normalize_recipe_ingredients([raw(amount=raw_amount)])
    assert result.unresolved == []
    assert result.ingredients[0].amount == pytest.approx(expected)


@pytest.mark.parametrize(
    "raw_amount",
    ["a splash", "", "   ", None, "1/0", True, [1, 2]],
)
def test_normalize_reports_unparseable_amount_as_unresolved(raw_amount):
    result = normalize_recipe_ingredients([raw(amount=raw_amount)])
    assert result.ingredients == []
    assert len(result.unresolved) == 1
    assert result.unresolved[0].reason == "invalid_amount"


@pytest.mark.parametrize("raw_amount", [0, -5, 10_001])
def test_normalize_reports_out_of_range_amount_as_unresolved(raw_amount):
    result = normalize_recipe_ingredients([raw(amount=raw_amount)])
    assert result.ingredients == []
    assert len(result.unresolved) == 1
    assert result.unresolved[0].reason == "invalid_amount"


# ---------------------------------------------------------------------------
# Ingredient identity: registry resolution, Unicode names, unresolved ids.
# ---------------------------------------------------------------------------


def test_normalize_resolves_known_ingredient_case_and_diacritic_insensitively():
    registry = IngredientRegistry([{"id": "ing-lime-juice", "name": "Chanh Dây"}])
    result = normalize_recipe_ingredients(
        [raw(display_name="  chanh DÂY  ", unit="ml", amount=20)],
        ingredient_registry=registry,
    )
    assert result.unresolved == []
    ingredient = result.ingredients[0]
    assert ingredient.normalized_ingredient_id == "ing-lime-juice"
    # Original bartender-entered text is preserved verbatim (only stripped).
    assert ingredient.display_name == "chanh DÂY"


def test_normalize_preserves_unicode_display_name_without_registry_match():
    result = normalize_recipe_ingredients(
        [raw(display_name="Crème de Cassis", unit="ml", amount=15)]
    )
    assert result.unresolved == []
    ingredient = result.ingredients[0]
    assert ingredient.display_name == "Crème de Cassis"
    assert ingredient.normalized_ingredient_id is None
    assert any("Crème de Cassis" in note for note in result.missing_data)


def test_normalize_reports_missing_display_name_as_unresolved():
    result = normalize_recipe_ingredients([raw(display_name="   ")])
    assert result.ingredients == []
    assert result.unresolved[0].reason == "missing_display_name"


# ---------------------------------------------------------------------------
# Duplicate ingredients: each line normalizes independently, in order.
# ---------------------------------------------------------------------------


def test_normalize_keeps_duplicate_ingredient_lines_separate_and_in_order():
    registry = IngredientRegistry([{"id": "ing-gin", "name": "Gin"}])
    result = normalize_recipe_ingredients(
        [
            raw(display_name="Gin", amount=45, unit="ml"),
            raw(display_name="Gin", amount=15, unit="ml"),
        ],
        ingredient_registry=registry,
    )
    assert result.unresolved == []
    assert [i.amount for i in result.ingredients] == [45.0, 15.0]
    assert all(i.normalized_ingredient_id == "ing-gin" for i in result.ingredients)


def test_normalize_processes_lines_independently_when_one_is_unresolved():
    result = normalize_recipe_ingredients(
        [
            raw(display_name="Gin", amount=45, unit="ml"),
            raw(display_name="Mystery Bitters", amount=2, unit="oz"),
        ]
    )
    assert len(result.ingredients) == 1
    assert result.ingredients[0].display_name == "Gin"
    assert len(result.unresolved) == 1
    assert result.unresolved[0].index == 1
    assert result.unresolved[0].display_name == "Mystery Bitters"


def test_normalize_accepts_plain_dict_input():
    result = normalize_recipe_ingredients(
        [{"display_name": "Simple Syrup", "amount": 15, "unit": "ml"}]
    )
    assert result.unresolved == []
    assert result.ingredients[0].display_name == "Simple Syrup"


def test_normalize_empty_input_returns_empty_result():
    result = normalize_recipe_ingredients([])
    assert result.ingredients == []
    assert result.unresolved == []
    assert result.missing_data == []
