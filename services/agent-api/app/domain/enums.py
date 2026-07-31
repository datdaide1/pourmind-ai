"""Versioned vocabulary for the regular-guest intelligence domain.

String enums are used deliberately so persisted JSON and generated OpenAPI use
stable, language-neutral values.
"""

from enum import Enum


class DomainEnum(str, Enum):
    """Base class that serializes naturally in JSON and Pydantic."""


class RecipeSource(DomainEnum):
    GLOBAL = "global"
    HOUSE = "house"
    BESPOKE = "bespoke"


class RecipeStatus(DomainEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class MenuStatus(DomainEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class PatronStatus(DomainEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConfidenceLabel(DomainEnum):
    NO_DATA = "no_data"
    LOW = "low"
    EMERGING = "emerging"
    MODERATE = "moderate"
    HIGH = "high"


class RecommendationStatus(DomainEnum):
    GENERATED = "generated"
    SAVED = "saved"
    SERVED = "served"
    DISMISSED = "dismissed"


class IngredientUnit(DomainEnum):
    ML = "ml"
    DASH = "dash"
    DROP = "drop"
    BARSPOON = "barspoon"
    PIECE = "piece"


class FeedbackProvenance(DomainEnum):
    GUEST_STATED = "guest_stated"
    BARTENDER_OBSERVED = "bartender_observed"


class FlavorProvenance(DomainEnum):
    CURATED = "curated"
    DATASET_DERIVED = "dataset_derived"
    BARTENDER_CONFIRMED = "bartender_confirmed"
    INFERRED = "inferred"


class CandidateSource(DomainEnum):
    ACTIVE_MENU = "menu"
    HOUSE_LIBRARY = "house"
    GLOBAL_RETRIEVAL = "global"
    AGENT_GENERATED = "generated"
