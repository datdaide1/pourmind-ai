import uuid

import pytest

from app.db.ingest_data import run_schema_migrations
from app.db.models import Bar, Menu, MenuItem, Recipe
from app.db.postgres import AsyncSessionLocal
from app.domain.enums import MenuStatus, RecipeSource, RecipeStatus
from app.repositories.bar_scoped import InvalidPageCursorError, menu_items, recipes


@pytest.fixture(scope="module", autouse=True)
async def setup_schema():
    await run_schema_migrations()


async def _make_bar(session, name: str) -> Bar:
    bar = Bar(name=name)
    session.add(bar)
    await session.flush()
    return bar


async def _make_recipe(session, *, bar_id, name: str, status: str = RecipeStatus.ACTIVE.value):
    recipe = Recipe(bar_id=bar_id, source=RecipeSource.HOUSE.value, name=name, status=status)
    session.add(recipe)
    await session.flush()
    return recipe


@pytest.mark.asyncio
async def test_get_never_resolves_a_resource_from_another_bar():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            bar_a = await _make_bar(session, f"Bar A {uuid.uuid4()}")
            bar_b = await _make_bar(session, f"Bar B {uuid.uuid4()}")
            # Two bars deliberately use the exact same recipe name.
            recipe_a = await _make_recipe(session, bar_id=bar_a.id, name="Old Fashioned")
            recipe_b = await _make_recipe(session, bar_id=bar_b.id, name="Old Fashioned")

        async with session.begin():
            found_own = await recipes.get(session, bar_id=bar_a.id, resource_id=recipe_a.id)
            assert found_own is not None
            assert found_own.id == recipe_a.id

            # recipe_b.id genuinely exists in the table, but not under bar_a.
            cross_bar = await recipes.get(session, bar_id=bar_a.id, resource_id=recipe_b.id)
            assert cross_bar is None

            nonexistent = await recipes.get(session, bar_id=bar_a.id, resource_id=uuid.uuid4())
            assert nonexistent is None


@pytest.mark.asyncio
async def test_list_paginated_only_returns_the_requesting_bars_rows():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            bar_a = await _make_bar(session, f"Bar A {uuid.uuid4()}")
            bar_b = await _make_bar(session, f"Bar B {uuid.uuid4()}")
            await _make_recipe(session, bar_id=bar_a.id, name="Daiquiri")
            for i in range(3):
                await _make_recipe(session, bar_id=bar_b.id, name=f"Bar B Recipe {i}")

        async with session.begin():
            page = await recipes.list_paginated(session, bar_id=bar_a.id, limit=50)
            assert len(page.items) == 1
            assert page.items[0].bar_id == bar_a.id
            assert page.next_cursor is None


@pytest.mark.asyncio
async def test_pagination_boundary_and_empty_page():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            bar = await _make_bar(session, f"Bar Pagination {uuid.uuid4()}")
            created = []
            for i in range(5):
                r = await _make_recipe(session, bar_id=bar.id, name=f"Recipe {i}")
                created.append(r)

        collected_ids = []
        cursor = None
        async with session.begin():
            page = await recipes.list_paginated(session, bar_id=bar.id, limit=2, cursor=cursor)
        assert len(page.items) == 2
        assert page.next_cursor is not None
        collected_ids.extend(item.id for item in page.items)
        cursor = page.next_cursor

        async with session.begin():
            page = await recipes.list_paginated(session, bar_id=bar.id, limit=2, cursor=cursor)
        assert len(page.items) == 2
        assert page.next_cursor is not None
        collected_ids.extend(item.id for item in page.items)
        cursor = page.next_cursor

        async with session.begin():
            page = await recipes.list_paginated(session, bar_id=bar.id, limit=2, cursor=cursor)
        assert len(page.items) == 1
        assert page.next_cursor is None
        collected_ids.extend(item.id for item in page.items)

        # No row skipped or repeated across the paged walk.
        assert set(collected_ids) == {r.id for r in created}
        assert len(collected_ids) == len(created)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            empty_bar = await _make_bar(session, f"Bar Empty {uuid.uuid4()}")

        async with session.begin():
            page = await recipes.list_paginated(session, bar_id=empty_bar.id, limit=10)
        assert page.items == []
        assert page.next_cursor is None


@pytest.mark.asyncio
async def test_archived_resources_excluded_by_default_and_included_explicitly():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            bar = await _make_bar(session, f"Bar Archive {uuid.uuid4()}")
            await _make_recipe(session, bar_id=bar.id, name="Active One", status=RecipeStatus.ACTIVE.value)
            await _make_recipe(session, bar_id=bar.id, name="Archived One", status=RecipeStatus.ARCHIVED.value)

        async with session.begin():
            default_page = await recipes.list_paginated(session, bar_id=bar.id, limit=10)
            assert len(default_page.items) == 1
            assert default_page.items[0].status == RecipeStatus.ACTIVE.value

            with_archived = await recipes.list_paginated(session, bar_id=bar.id, limit=10, include_archived=True)
            assert len(with_archived.items) == 2


@pytest.mark.asyncio
async def test_cursor_from_another_bar_is_rejected():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            bar_a = await _make_bar(session, f"Bar A {uuid.uuid4()}")
            bar_b = await _make_bar(session, f"Bar B {uuid.uuid4()}")
            recipe_b = await _make_recipe(session, bar_id=bar_b.id, name="Not Yours")

        async with session.begin():
            with pytest.raises(InvalidPageCursorError):
                await recipes.list_paginated(session, bar_id=bar_a.id, limit=10, cursor=str(recipe_b.id))


@pytest.mark.asyncio
async def test_create_requires_bar_id_and_update_is_scoped():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            bar_a = await _make_bar(session, f"Bar A {uuid.uuid4()}")
            bar_b = await _make_bar(session, f"Bar B {uuid.uuid4()}")

        async with session.begin():
            with pytest.raises(ValueError):
                await recipes.create(
                    session,
                    Recipe(bar_id=None, source=RecipeSource.HOUSE.value, name="Orphan", status=RecipeStatus.DRAFT.value),
                )

        async with session.begin():
            created = await recipes.create(
                session,
                Recipe(bar_id=bar_a.id, source=RecipeSource.HOUSE.value, name="Margarita", status=RecipeStatus.DRAFT.value),
            )

        async with session.begin():
            # bar_b cannot update a recipe it does not own.
            result = await recipes.update(
                session, bar_id=bar_b.id, resource_id=created.id, values={"name": "Hijacked"}
            )
            assert result is None

            updated = await recipes.update(
                session, bar_id=bar_a.id, resource_id=created.id, values={"status": RecipeStatus.ACTIVE.value}
            )
            assert updated is not None
            assert updated.status == RecipeStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_relation_scoped_menu_items_require_parent_bar_ownership():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            bar_a = await _make_bar(session, f"Bar A {uuid.uuid4()}")
            bar_b = await _make_bar(session, f"Bar B {uuid.uuid4()}")
            recipe_a = await _make_recipe(session, bar_id=bar_a.id, name="House Old Fashioned")
            menu_a = Menu(bar_id=bar_a.id, name="Main Menu", status=MenuStatus.ACTIVE.value)
            session.add(menu_a)
            await session.flush()

        async with session.begin():
            item = await menu_items.create_for_parent(
                session,
                bar_id=bar_a.id,
                parent_id=menu_a.id,
                instance=MenuItem(menu_id=menu_a.id, recipe_id=recipe_a.id, display_name="Old Fashioned"),
            )

        async with session.begin():
            # bar_b cannot see bar_a's menu item even with the right item id.
            cross_bar = await menu_items.get(session, bar_id=bar_b.id, resource_id=item.id)
            assert cross_bar is None

            own = await menu_items.get(session, bar_id=bar_a.id, resource_id=item.id)
            assert own is not None
            assert own.id == item.id

            # Creating a child under a parent owned by a different bar is refused.
            with pytest.raises(ValueError):
                await menu_items.create_for_parent(
                    session,
                    bar_id=bar_b.id,
                    parent_id=menu_a.id,
                    instance=MenuItem(menu_id=menu_a.id, recipe_id=recipe_a.id, display_name="Stolen"),
                )
