from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain.schemas import IngredientLine, RecipeCreate, RecipeSnapshot


def ingredient(**overrides):
    values = {"display_name": "Gin", "amount": 45, "unit": "ml"}
    values.update(overrides)
    return values


def test_recipe_accepts_supported_units_and_bounds():
    for unit in ("ml", "dash", "drop", "barspoon", "piece"):
        line = IngredientLine(**ingredient(unit=unit))
        assert line.unit == unit


@pytest.mark.parametrize(
    ("field", "value"),
    [("unit", "oz"), ("amount", 0), ("amount", -1)],
)
def test_ingredient_rejects_invalid_unit_or_quantity(field, value):
    with pytest.raises(ValidationError):
        IngredientLine(**ingredient(**{field: value}))


def test_recipe_requires_at_least_one_ingredient_and_rejects_extra_fields():
    with pytest.raises(ValidationError):
        RecipeCreate(name="Martini", source="house", ingredients=[])
    with pytest.raises(ValidationError):
        RecipeCreate(
            name="Martini",
            source="house",
            ingredients=[ingredient()],
            unknown="not allowed",
        )


def test_recipe_snapshot_has_versioned_contract():
    snapshot = RecipeSnapshot(
        recipe_id=uuid4(),
        recipe_version_id=uuid4(),
        version_number=1,
        name="Martini",
        source="house",
        ingredients=[ingredient()],
        flavor_profile={"dimensions": {"dry": 80}},
    )
    assert snapshot.schema_version == "recipe-snapshot-v1"


def test_recipe_snapshot_rejects_invalid_abv():
    with pytest.raises(ValidationError):
        RecipeSnapshot(
            version_number=1,
            name="Impossible",
            source="house",
            ingredients=[ingredient()],
            flavor_profile={},
            estimated_abv=101,
        )


def test_invalid_recipe_payload_has_stable_422_shape():
    app = FastAPI()

    @app.post("/recipes")
    def create_recipe(payload: RecipeCreate):
        return payload

    response = TestClient(app).post(
        "/recipes",
        json={
            "name": "Invalid",
            "source": "unknown",
            "ingredients": [ingredient(amount=-1, unit="oz")],
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert {(error["loc"][-1], error["type"]) for error in errors} == {
        ("source", "enum"),
        ("amount", "greater_than"),
        ("unit", "enum"),
    }
