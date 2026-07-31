from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain.schemas import IngredientLine, RecipeCreate, RecipeSnapshot
from app.main import app as production_app


def ingredient(**overrides):
    values = {"display_name": "Gin", "amount": 45, "unit": "ml"}
    values.update(overrides)
    return values


def flavor_profile(**dimension_overrides):
    dimensions = {
        "sweet": 0.1,
        "sour": 0.2,
        "bitter": 0.3,
        "spirituous": 0.8,
        "fruity": 0.1,
        "herbal": 0.2,
        "spicy": 0.0,
        "smoky": 0.0,
    }
    dimensions.update(dimension_overrides)
    return {
        "taxonomy_version": "flavor-v1",
        "dimensions": dimensions,
        "provenance": ["curated"],
    }


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
        flavor_profile=flavor_profile(),
    )
    assert snapshot.schema_version == "recipe-snapshot-v1"
    assert snapshot.flavor_profile.taxonomy_version == "flavor-v1"


def test_recipe_snapshot_rejects_invalid_abv():
    with pytest.raises(ValidationError):
        RecipeSnapshot(
            version_number=1,
            name="Impossible",
            source="house",
            ingredients=[ingredient()],
            flavor_profile=flavor_profile(),
            estimated_abv=101,
        )


def test_flavor_profile_rejects_unknown_dimensions_and_non_normalized_values():
    with pytest.raises(ValidationError):
        RecipeSnapshot(
            version_number=1,
            name="Invalid taxonomy",
            source="house",
            ingredients=[ingredient()],
            flavor_profile=flavor_profile(dry=0.5),
        )
    with pytest.raises(ValidationError):
        RecipeSnapshot(
            version_number=1,
            name="Invalid scale",
            source="house",
            ingredients=[ingredient()],
            flavor_profile=flavor_profile(sweet=50),
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


def test_domain_contracts_are_published_in_application_openapi():
    schemas = production_app.openapi()["components"]["schemas"]
    expected = {
        "RecipeCreate",
        "RecipeSnapshot",
        "PatronCreate",
        "RecommendationResponse",
    }
    assert expected <= schemas.keys()


def test_application_uses_stable_422_for_constraint_errors():
    response = TestClient(production_app).post(
        "/api/v1/tools/calculate_cost",
        json={"recipe": [{"ingredient": "Gin", "amount_ml": -1}]},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "greater_than"
