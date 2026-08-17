"""Bar-scoped repository and query helpers (FND-05).

Centralizes bar-scoped reads and writes so endpoint/service code cannot
accidentally query a table by resource UUID alone. Every lookup and list
helper requires `(bar_id, resource_id)`, or an equivalent bar-scoped
relationship for child tables that carry no `bar_id` column of their own.
This mirrors the fail-closed, non-enumerating posture app/core/bar_auth.py
(FND-03) established for principal resolution: a resource that belongs to
another bar must behave exactly like a resource that does not exist.

Repository methods never open or commit a transaction themselves — they
`add`/`execute`/`flush` on the AsyncSession the caller passes in, the same
convention app/db/ingest_data.py uses (`async with session.begin(): ...`
is the caller's responsibility). This keeps a request's writes inside one
transaction instead of each helper committing independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Optional, Sequence, TypeVar
from uuid import UUID

from sqlalchemy import Select, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.db.models import (
    BarMembership,
    DrinkExperience,
    Menu,
    MenuItem,
    Patron,
    Recipe,
    RecipeVersion,
    Recommendation,
)
from app.domain.enums import MenuStatus, PatronStatus, RecipeStatus

ModelT = TypeVar("ModelT")

# Bounded so a caller can never force an unbounded scan by passing a huge limit.
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100


class InvalidPageCursorError(ValueError):
    """Raised when a caller supplies a cursor that does not resolve to a row
    this bar can see (forged, stale, or belonging to another bar)."""


@dataclass(frozen=True, slots=True)
class Page(Generic[ModelT]):
    items: list[ModelT]
    next_cursor: Optional[str]


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_PAGE_LIMIT))


@dataclass(frozen=True, slots=True)
class BarScopedRepository(Generic[ModelT]):
    """Generic repository over a table that carries `bar_id` directly.

    `order_column` provides the primary sort; `id_column` is always the
    tie-breaker, so pagination stays stable even when many rows share the
    same `order_column` value (e.g. bulk-inserted in the same transaction).
    """

    model: type[ModelT]
    id_column: InstrumentedAttribute
    bar_id_column: InstrumentedAttribute
    order_column: InstrumentedAttribute
    status_column: Optional[InstrumentedAttribute] = None
    archived_value: Optional[str] = None

    async def get(self, session: AsyncSession, *, bar_id: UUID, resource_id: UUID) -> Optional[ModelT]:
        """Scoped lookup. A resource that belongs to another bar resolves to
        None exactly like a resource that does not exist at all."""
        stmt = select(self.model).where(
            self.id_column == resource_id,
            self.bar_id_column == bar_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        session: AsyncSession,
        *,
        bar_id: UUID,
        limit: int = DEFAULT_PAGE_LIMIT,
        cursor: Optional[str] = None,
        include_archived: bool = False,
        extra_filters: Sequence[Any] = (),
    ) -> Page[ModelT]:
        bounded_limit = _clamp_limit(limit)
        stmt: Select = select(self.model).where(self.bar_id_column == bar_id, *extra_filters)

        if self.status_column is not None and self.archived_value is not None and not include_archived:
            stmt = stmt.where(self.status_column != self.archived_value)

        if cursor is not None:
            anchor_order_value, anchor_id_value = await self._resolve_cursor(session, bar_id=bar_id, cursor=cursor)
            stmt = stmt.where(
                tuple_(self.order_column, self.id_column) > tuple_(anchor_order_value, anchor_id_value)
            )

        stmt = stmt.order_by(self.order_column.asc(), self.id_column.asc()).limit(bounded_limit + 1)

        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor = None
        if len(rows) > bounded_limit:
            rows = rows[:bounded_limit]
            next_cursor = str(getattr(rows[-1], self.id_column.key))

        return Page(items=rows, next_cursor=next_cursor)

    async def _resolve_cursor(self, session: AsyncSession, *, bar_id: UUID, cursor: str):
        """Cursors are opaque resource IDs; the anchor row's own ordering
        values are read back from the database rather than parsed out of
        the cursor, so no per-column type decoding is needed. Scoping the
        anchor lookup by bar_id means a cursor from another bar is simply
        invalid here, never a cross-bar information leak."""
        try:
            anchor_id = UUID(cursor)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidPageCursorError("Malformed pagination cursor") from exc

        stmt = select(self.order_column, self.id_column).where(
            self.id_column == anchor_id,
            self.bar_id_column == bar_id,
        )
        result = await session.execute(stmt)
        row = result.first()
        if row is None:
            raise InvalidPageCursorError("Pagination cursor does not resolve to a visible row")
        return row[0], row[1]

    async def create(self, session: AsyncSession, instance: ModelT) -> ModelT:
        """Defensive create: refuses to persist a row with no bar_id set,
        so a bug upstream cannot silently create an unscoped/orphan row."""
        if getattr(instance, self.bar_id_column.key) is None:
            raise ValueError(f"{self.model.__name__} must have {self.bar_id_column.key} set before create()")
        session.add(instance)
        await session.flush()
        return instance

    async def update(
        self, session: AsyncSession, *, bar_id: UUID, resource_id: UUID, values: dict[str, Any]
    ) -> Optional[ModelT]:
        """Scoped update: composes get(), so a caller can never update a
        row it could not have looked up. Refuses to touch bar_id or id: a
        `values` dict that tried to re-scope or re-identify the row would
        silently defeat the whole point of a bar-scoped repository."""
        immutable_keys = {self.bar_id_column.key, self.id_column.key} & values.keys()
        if immutable_keys:
            raise ValueError(f"update() cannot modify immutable fields: {sorted(immutable_keys)}")

        instance = await self.get(session, bar_id=bar_id, resource_id=resource_id)
        if instance is None:
            return None
        for key, value in values.items():
            setattr(instance, key, value)
        await session.flush()
        return instance

    async def archive(self, session: AsyncSession, *, bar_id: UUID, resource_id: UUID) -> Optional[ModelT]:
        if self.status_column is None or self.archived_value is None:
            raise NotImplementedError(f"{self.model.__name__} has no archived status configured")
        return await self.update(
            session, bar_id=bar_id, resource_id=resource_id, values={self.status_column.key: self.archived_value}
        )


@dataclass(frozen=True, slots=True)
class RelationBarScopedRepository(Generic[ModelT]):
    """Repository for a child table with no `bar_id` column of its own
    (e.g. menu_items, recipe_versions): scope is proven by joining to the
    parent row and checking the parent's bar_id."""

    model: type[ModelT]
    id_column: InstrumentedAttribute
    parent_fk_column: InstrumentedAttribute
    order_column: InstrumentedAttribute
    parent_model: type[Any]
    parent_id_column: InstrumentedAttribute
    parent_bar_id_column: InstrumentedAttribute

    async def get(self, session: AsyncSession, *, bar_id: UUID, resource_id: UUID) -> Optional[ModelT]:
        stmt = (
            select(self.model)
            .join(self.parent_model, self.parent_fk_column == self.parent_id_column)
            .where(self.id_column == resource_id, self.parent_bar_id_column == bar_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_parent(
        self,
        session: AsyncSession,
        *,
        bar_id: UUID,
        parent_id: UUID,
        limit: int = DEFAULT_PAGE_LIMIT,
        cursor: Optional[str] = None,
    ) -> Page[ModelT]:
        bounded_limit = _clamp_limit(limit)
        stmt: Select = (
            select(self.model)
            .join(self.parent_model, self.parent_fk_column == self.parent_id_column)
            .where(self.parent_fk_column == parent_id, self.parent_bar_id_column == bar_id)
        )

        if cursor is not None:
            anchor_order_value, anchor_id_value = await self._resolve_cursor(
                session, bar_id=bar_id, parent_id=parent_id, cursor=cursor
            )
            stmt = stmt.where(
                tuple_(self.order_column, self.id_column) > tuple_(anchor_order_value, anchor_id_value)
            )

        stmt = stmt.order_by(self.order_column.asc(), self.id_column.asc()).limit(bounded_limit + 1)

        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor = None
        if len(rows) > bounded_limit:
            rows = rows[:bounded_limit]
            next_cursor = str(getattr(rows[-1], self.id_column.key))

        return Page(items=rows, next_cursor=next_cursor)

    async def _resolve_cursor(self, session: AsyncSession, *, bar_id: UUID, parent_id: UUID, cursor: str):
        try:
            anchor_id = UUID(cursor)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidPageCursorError("Malformed pagination cursor") from exc

        stmt = (
            select(self.order_column, self.id_column)
            .join(self.parent_model, self.parent_fk_column == self.parent_id_column)
            .where(
                self.id_column == anchor_id,
                self.parent_fk_column == parent_id,
                self.parent_bar_id_column == bar_id,
            )
        )
        result = await session.execute(stmt)
        row = result.first()
        if row is None:
            raise InvalidPageCursorError("Pagination cursor does not resolve to a visible row")
        return row[0], row[1]

    async def create_for_parent(
        self, session: AsyncSession, *, bar_id: UUID, parent_id: UUID, instance: ModelT
    ) -> ModelT:
        """Defensive create: verifies the parent belongs to this bar, and
        that `instance` is actually wired to that same parent, before
        persisting the child row. Without the second check, a caller could
        pass a bar-owned `parent_id` to satisfy the ownership guard while
        `instance` still points at a different (possibly foreign) parent."""
        parent_stmt = select(self.parent_id_column).where(
            self.parent_id_column == parent_id, self.parent_bar_id_column == bar_id
        )
        parent_row = (await session.execute(parent_stmt)).first()
        if parent_row is None:
            raise ValueError(f"{self.parent_model.__name__} {parent_id} not found for bar {bar_id}")

        parent_fk_attr = self.parent_fk_column.key
        instance_parent_id = getattr(instance, parent_fk_attr, None)
        if instance_parent_id is not None and instance_parent_id != parent_id:
            raise ValueError(
                f"{type(instance).__name__}.{parent_fk_attr} ({instance_parent_id}) does not match "
                f"parent_id ({parent_id})"
            )
        setattr(instance, parent_fk_attr, parent_id)

        session.add(instance)
        await session.flush()
        return instance


# --- Pre-built repositories for the FND-04 bar-scoped tables ---------------
# TasteProfile is intentionally not represented here: it is a one-per-patron
# singleton keyed by patron_id, not a listable bar-scoped collection, so it
# does not fit either shape above. The INT tasks that read/write it can get
# a row directly via patron_id + bar_id equality.

bar_memberships = BarScopedRepository(
    model=BarMembership,
    id_column=BarMembership.id,
    bar_id_column=BarMembership.bar_id,
    order_column=BarMembership.created_at,
)

recipes = BarScopedRepository(
    model=Recipe,
    id_column=Recipe.id,
    bar_id_column=Recipe.bar_id,
    order_column=Recipe.created_at,
    status_column=Recipe.status,
    archived_value=RecipeStatus.ARCHIVED.value,
)

menus = BarScopedRepository(
    model=Menu,
    id_column=Menu.id,
    bar_id_column=Menu.bar_id,
    order_column=Menu.created_at,
    status_column=Menu.status,
    archived_value=MenuStatus.ARCHIVED.value,
)

patrons = BarScopedRepository(
    model=Patron,
    id_column=Patron.id,
    bar_id_column=Patron.bar_id,
    order_column=Patron.created_at,
    status_column=Patron.status,
    archived_value=PatronStatus.ARCHIVED.value,
)

drink_experiences = BarScopedRepository(
    model=DrinkExperience,
    id_column=DrinkExperience.id,
    bar_id_column=DrinkExperience.bar_id,
    order_column=DrinkExperience.served_at,
)

recommendations = BarScopedRepository(
    model=Recommendation,
    id_column=Recommendation.id,
    bar_id_column=Recommendation.bar_id,
    order_column=Recommendation.created_at,
)

recipe_versions = RelationBarScopedRepository(
    model=RecipeVersion,
    id_column=RecipeVersion.id,
    parent_fk_column=RecipeVersion.recipe_id,
    order_column=RecipeVersion.version_number,
    parent_model=Recipe,
    parent_id_column=Recipe.id,
    parent_bar_id_column=Recipe.bar_id,
)

menu_items = RelationBarScopedRepository(
    model=MenuItem,
    id_column=MenuItem.id,
    parent_fk_column=MenuItem.menu_id,
    order_column=MenuItem.sort_order,
    parent_model=Menu,
    parent_id_column=Menu.id,
    parent_bar_id_column=Menu.bar_id,
)
