import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Text,
    Boolean,
    Float,
    Integer,
    SmallInteger,
    ForeignKey,
    DateTime,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.domain.enums import (
    ConfidenceLabel,
    FeedbackProvenance,
    MenuStatus,
    PatronStatus,
    RecipeSource,
    RecipeStatus,
    RecommendationStatus,
)

class Base(DeclarativeBase):
    pass


def _enum_values_sql(column: str, enum_cls) -> str:
    """Render `column IN ('a', 'b', ...)` from a domain enum.

    Keeps CHECK constraints from silently drifting out of sync with the
    FND-02 domain vocabulary in app/domain/enums.py.
    """
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return f"{column} IN ({values})"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat", server_default="New Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    ip_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)

    messages: Mapped[List["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ui_blocks: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_alcoholic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    abv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

class LiquorPrice(Base):
    __tablename__ = "liquor_prices"
    __table_args__ = (
        # Stable natural key so ingestion can upsert instead of delete-and-reinsert.
        UniqueConstraint("name", "size_raw", name="uq_liquor_prices_name_size_raw"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    size_raw: Mapped[str] = mapped_column(String(50), nullable=False)
    size_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    price_vnd: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_ml_vnd: Mapped[float] = mapped_column(Float, nullable=False)

class MixologyRule(Base):
    __tablename__ = "mixology_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    substitutes: Mapped[List[str]] = mapped_column(JSONB, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# --- Regular Guest Intelligence (FND-04) ------------------------------------
# Table layout follows docs/REGULAR_GUEST_INTELLIGENCE_MVP_SPEC.md #12 "Data
# model proposal". CHECK constraints reuse the FND-02 domain enums so the
# database can never accept a value the application layer would reject.

class Bar(Base):
    __tablename__ = "bars"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BarMembership(Base):
    __tablename__ = "bar_memberships"
    __table_args__ = (
        UniqueConstraint("bar_id", "user_id", name="uq_bar_memberships_bar_user"),
        CheckConstraint("role IN ('owner', 'manager', 'bartender')", name="ck_bar_memberships_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint(_enum_values_sql("source", RecipeSource), name="ck_recipes_source"),
        CheckConstraint(_enum_values_sql("status", RecipeStatus), name="ck_recipes_status"),
        Index("ix_recipes_bar_id", "bar_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # NULL only for persisted global records; every house/bespoke recipe is bar-owned.
    bar_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("bars.id", ondelete="CASCADE"), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    # No FK: the referenced recipe_versions row is created after this row and
    # a circular FK between recipes and recipe_versions is unnecessary here.
    current_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    derived_from_recipe_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    versions: Mapped[List["RecipeVersion"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", foreign_keys="RecipeVersion.recipe_id"
    )


class RecipeVersion(Base):
    __tablename__ = "recipe_versions"
    __table_args__ = (
        UniqueConstraint("recipe_id", "version_number", name="uq_recipe_versions_recipe_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ingredients: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    technique: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    glassware: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    garnish: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flavor_profile: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    total_volume_ml: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_abv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_cost_vnd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calculation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe: Mapped["Recipe"] = relationship(back_populates="versions", foreign_keys=[recipe_id])


class Menu(Base):
    __tablename__ = "menus"
    __table_args__ = (
        CheckConstraint(_enum_values_sql("status", MenuStatus), name="ck_menus_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = (
        # MVP: a recipe appears at most once per menu.
        UniqueConstraint("menu_id", "recipe_id", name="uq_menu_items_menu_recipe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    selling_price_vnd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class Patron(Base):
    __tablename__ = "patrons"
    __table_args__ = (
        CheckConstraint(_enum_values_sql("status", PatronStatus), name="ck_patrons_status"),
        Index("ix_patrons_bar_id_display_name", "bar_id", "display_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pronouns: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    service_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allergies: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True)
    avoidances: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # Pilot requires affirmative notice opt-in (FND-01 decision D4); the
    # acknowledging principal is recorded, never inferred.
    notice_acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notice_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notice_acknowledged_by_principal: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class DrinkExperience(Base):
    __tablename__ = "drink_experiences"
    __table_args__ = (
        CheckConstraint("rating IS NULL OR (rating BETWEEN 1 AND 5)", name="ck_drink_experiences_rating_range"),
        CheckConstraint(
            "feedback_provenance IS NULL OR " + _enum_values_sql("feedback_provenance", FeedbackProvenance),
            name="ck_drink_experiences_feedback_provenance_values",
        ),
        # FND-01 decision D2: rating/feedback requires stated provenance.
        CheckConstraint(
            "(rating IS NULL AND feedback IS NULL) OR feedback_provenance IS NOT NULL",
            name="ck_drink_experiences_provenance_required",
        ),
        UniqueConstraint("bar_id", "idempotency_key", name="uq_drink_experiences_bar_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    patron_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patrons.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    recipe_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("recipe_versions.id", ondelete="SET NULL"), nullable=True)
    # Server-built snapshot (PTR-03); the source of truth even if the recipe
    # is edited or deleted later.
    recipe_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_provenance: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    served_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TasteProfile(Base):
    __tablename__ = "taste_profiles"
    __table_args__ = (
        CheckConstraint(
            "confidence_label IS NULL OR " + _enum_values_sql("confidence_label", ConfidenceLabel),
            name="ck_taste_profiles_confidence_label",
        ),
    )

    patron_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patrons.id", ondelete="CASCADE"), primary_key=True)
    bar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    profile: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    evidence_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    eligible_experience_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_label: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    profile_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    computed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(_enum_values_sql("status", RecommendationStatus), name="ck_recommendations_status"),
        Index("ix_recommendations_bar_patron", "bar_id", "patron_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    patron_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patrons.id", ondelete="CASCADE"), nullable=False)
    candidate_recipe_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generated", server_default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
