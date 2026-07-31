"""Expose shared domain contracts without registering unfinished API routes."""

from typing import Union

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import TypeAdapter

from app.domain.schemas import (
    DrinkExperience,
    DrinkExperienceCreate,
    Menu,
    MenuCreate,
    Patron,
    PatronCreate,
    RecipeCreate,
    RecipeSnapshot,
    RecipeSummary,
    RecipeVersion,
    RecommendationResponse,
    TasteProfile,
)

DomainContract = Union[
    RecipeCreate,
    RecipeSummary,
    RecipeVersion,
    RecipeSnapshot,
    MenuCreate,
    Menu,
    PatronCreate,
    Patron,
    DrinkExperienceCreate,
    DrinkExperience,
    TasteProfile,
    RecommendationResponse,
]


def install_domain_openapi(app: FastAPI) -> None:
    """Add contract-only schemas while later tasks keep their routes disabled."""

    def domain_openapi() -> dict:
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
        )
        contract_schema = TypeAdapter(DomainContract).json_schema(
            ref_template="#/components/schemas/{model}"
        )
        definitions = contract_schema.get("$defs", {})
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        for name, definition in definitions.items():
            # Prefer FastAPI's route-bound definition once a later task
            # registers the real endpoint for the same model.
            components.setdefault(name, definition)
        app.openapi_schema = schema
        return schema

    app.openapi = domain_openapi
