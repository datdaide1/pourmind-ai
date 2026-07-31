"""Pydantic contracts shared by regular-guest API and service layers."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import (
    CandidateSource,
    ConfidenceLabel,
    FeedbackProvenance,
    IngredientUnit,
    MenuStatus,
    PatronStatus,
    RecipeSource,
    RecipeStatus,
    RecommendationStatus,
)

SCHEMA_VERSION = "recipe-snapshot-v1"
PROFILE_VERSION = "taste-v1"
SCORING_VERSION = "match-v1"

Name = Annotated[str, Field(min_length=1, max_length=255)]
ShortText = Annotated[str, Field(min_length=1, max_length=500)]
Score = Annotated[float, Field(ge=0, le=100)]
NonNegativeMoney = Annotated[float, Field(ge=0)]
PositiveQuantity = Annotated[float, Field(gt=0, le=10_000)]


class DomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=True,
    )


class IngredientLine(DomainModel):
    display_name: Name
    normalized_ingredient_id: Annotated[
        str | None, Field(default=None, min_length=1, max_length=255)
    ]
    amount: PositiveQuantity
    unit: IngredientUnit


class FlavorProfile(DomainModel):
    dimensions: dict[Annotated[str, Field(min_length=1, max_length=64)], Score] = Field(
        default_factory=dict, max_length=32
    )
    tags: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(
        default_factory=list, max_length=32
    )
    missing_data: list[Annotated[str, Field(min_length=1, max_length=255)]] = Field(
        default_factory=list, max_length=50
    )


class RecipeVersionInput(DomainModel):
    ingredients: list[IngredientLine] = Field(min_length=1, max_length=100)
    technique: Annotated[str | None, Field(default=None, max_length=500)]
    glassware: Annotated[str | None, Field(default=None, max_length=255)]
    garnish: Annotated[str | None, Field(default=None, max_length=500)]
    description: Annotated[str | None, Field(default=None, max_length=2_000)]
    internal_notes: Annotated[str | None, Field(default=None, max_length=2_000)]
    flavor_profile: FlavorProfile = Field(default_factory=FlavorProfile)


class RecipeCreate(RecipeVersionInput):
    name: Name
    source: RecipeSource
    status: RecipeStatus = RecipeStatus.DRAFT
    derived_from_recipe_id: UUID | None = None

    @model_validator(mode="after")
    def validate_source_ownership(self) -> "RecipeCreate":
        if self.source == RecipeSource.GLOBAL and self.derived_from_recipe_id is not None:
            raise ValueError("global recipes cannot derive from another recipe")
        return self


class RecipeSummary(DomainModel):
    id: UUID
    bar_id: UUID | None
    name: Name
    source: RecipeSource
    status: RecipeStatus
    current_version_id: UUID
    derived_from_recipe_id: UUID | None = None


class RecipeVersion(RecipeVersionInput):
    id: UUID
    recipe_id: UUID
    version_number: Annotated[int, Field(ge=1)]
    total_volume_ml: Annotated[float | None, Field(default=None, gt=0, le=100_000)]
    estimated_abv: Annotated[float | None, Field(default=None, ge=0, le=100)]
    estimated_cost_vnd: NonNegativeMoney | None = None
    missing_data: list[Annotated[str, Field(min_length=1, max_length=255)]] = Field(
        default_factory=list, max_length=50
    )
    created_at: datetime


class RecipeSnapshot(DomainModel):
    schema_version: Annotated[
        str, Field(default=SCHEMA_VERSION, pattern=r"^recipe-snapshot-v\d+$")
    ]
    recipe_id: UUID | None = None
    recipe_version_id: UUID | None = None
    version_number: Annotated[int, Field(ge=1)]
    name: Name
    source: RecipeSource
    ingredients: list[IngredientLine] = Field(min_length=1, max_length=100)
    technique: Annotated[str | None, Field(default=None, max_length=500)]
    glassware: Annotated[str | None, Field(default=None, max_length=255)]
    garnish: Annotated[str | None, Field(default=None, max_length=500)]
    total_volume_ml: Annotated[float | None, Field(default=None, gt=0, le=100_000)]
    estimated_abv: Annotated[float | None, Field(default=None, ge=0, le=100)]
    estimated_cost_vnd: NonNegativeMoney | None = None
    flavor_profile: FlavorProfile
    missing_data: list[Annotated[str, Field(min_length=1, max_length=255)]] = Field(
        default_factory=list, max_length=50
    )


class MenuCreate(DomainModel):
    name: Name
    status: MenuStatus = MenuStatus.DRAFT


class MenuItemInput(DomainModel):
    recipe_id: UUID
    display_name: Name
    section: Annotated[str | None, Field(default=None, max_length=255)]
    selling_price_vnd: NonNegativeMoney | None = None
    is_available: bool = True
    sort_order: Annotated[int, Field(default=0, ge=0, le=100_000)]


class Menu(DomainModel):
    id: UUID
    bar_id: UUID
    name: Name
    status: MenuStatus
    items: list[MenuItemInput] = Field(default_factory=list, max_length=1_000)


class PatronCreate(DomainModel):
    display_name: Name
    pronouns: Annotated[str | None, Field(default=None, max_length=100)]
    service_notes: Annotated[str | None, Field(default=None, max_length=2_000)]
    allergies: list[ShortText] = Field(default_factory=list, max_length=100)
    avoidances: list[ShortText] = Field(default_factory=list, max_length=100)
    notice_version: Annotated[str, Field(min_length=1, max_length=32)]
    notice_acknowledged_at: datetime


class Patron(DomainModel):
    id: UUID
    bar_id: UUID
    status: PatronStatus
    display_name: Name
    pronouns: Annotated[str | None, Field(default=None, max_length=100)]
    service_notes: Annotated[str | None, Field(default=None, max_length=2_000)]
    allergies: list[ShortText] = Field(default_factory=list, max_length=100)
    avoidances: list[ShortText] = Field(default_factory=list, max_length=100)
    notice_version: Annotated[str, Field(min_length=1, max_length=32)]
    notice_acknowledged_at: datetime


class DrinkExperienceCreate(DomainModel):
    recipe_id: UUID | None = None
    recipe_version_id: UUID | None = None
    rating: Annotated[int | None, Field(default=None, ge=1, le=5)]
    feedback: Annotated[str | None, Field(default=None, max_length=2_000)]
    feedback_provenance: FeedbackProvenance | None = None
    served_at: datetime
    idempotency_key: Annotated[str, Field(min_length=1, max_length=255)]

    @model_validator(mode="after")
    def require_feedback_provenance(self) -> "DrinkExperienceCreate":
        if (self.rating is not None or self.feedback is not None) and (
            self.feedback_provenance is None
        ):
            raise ValueError(
                "feedback_provenance is required when rating or feedback is present"
            )
        if self.feedback_provenance is not None and (
            self.rating is None and self.feedback is None
        ):
            raise ValueError(
                "feedback_provenance requires a rating or feedback"
            )
        return self


class DrinkExperience(DomainModel):
    id: UUID
    bar_id: UUID
    patron_id: UUID
    recipe_snapshot: RecipeSnapshot
    rating: Annotated[int | None, Field(default=None, ge=1, le=5)]
    feedback: Annotated[str | None, Field(default=None, max_length=2_000)]
    feedback_provenance: FeedbackProvenance | None = None
    served_at: datetime


class TasteProfile(DomainModel):
    patron_id: UUID
    profile_version: Annotated[
        str, Field(default=PROFILE_VERSION, pattern=r"^taste-v\d+$")
    ]
    flavor_dimensions: dict[
        Annotated[str, Field(min_length=1, max_length=64)], Score
    ] = Field(default_factory=dict, max_length=32)
    preferred_base_spirits: list[ShortText] = Field(default_factory=list, max_length=50)
    liked_ingredients: list[ShortText] = Field(default_factory=list, max_length=100)
    disliked_ingredients: list[ShortText] = Field(default_factory=list, max_length=100)
    eligible_experience_count: Annotated[int, Field(ge=0)]
    confidence_score: Score
    confidence_label: ConfidenceLabel
    caveats: list[ShortText] = Field(default_factory=list, max_length=50)
    computed_at: datetime
    is_stale: bool = False


class ScoreComponent(DomainModel):
    score: Score
    weight: Annotated[float, Field(gt=0, le=1)]
    evidence_count: Annotated[int, Field(ge=0)]
    explanation_key: Annotated[str, Field(min_length=1, max_length=100)]


class Recommendation(DomainModel):
    id: UUID | None = None
    name: Name
    source: CandidateSource
    status: RecommendationStatus = RecommendationStatus.GENERATED
    candidate_recipe_snapshot: RecipeSnapshot
    match_score: Score
    confidence_score: Score
    confidence_label: ConfidenceLabel
    scoring_version: Annotated[
        str, Field(default=SCORING_VERSION, pattern=r"^match-v\d+$")
    ]
    components: dict[
        Annotated[str, Field(min_length=1, max_length=64)], ScoreComponent
    ] = Field(min_length=1, max_length=16)
    evidence_count: Annotated[int, Field(ge=0)]
    matched_preferences: list[ShortText] = Field(default_factory=list, max_length=50)
    novel_elements: list[ShortText] = Field(default_factory=list, max_length=50)
    caveats: list[ShortText] = Field(default_factory=list, max_length=50)
    hard_exclusions: list[ShortText] = Field(default_factory=list, max_length=50)


class RecommendationResponse(DomainModel):
    patron_id: UUID
    profile_version: Annotated[str, Field(pattern=r"^taste-v\d+$")]
    scoring_version: Annotated[str, Field(pattern=r"^match-v\d+$")]
    recommendations: list[Recommendation] = Field(max_length=3)

    @model_validator(mode="after")
    def require_consistent_scoring_version(self) -> "RecommendationResponse":
        if any(
            item.scoring_version != self.scoring_version
            for item in self.recommendations
        ):
            raise ValueError(
                "recommendation scoring_version must match response scoring_version"
            )
        return self
