from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.schemas import MenuCreate, MenuItemInput


def test_menu_and_item_accept_bounded_values():
    assert MenuCreate(name="Dinner", status="active").status == "active"
    item = MenuItemInput(
        recipe_id=uuid4(),
        display_name="House Martini",
        selling_price_vnd=180_000,
    )
    assert item.sort_order == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "status": "draft"},
        {"name": "Dinner", "status": "published"},
    ],
)
def test_menu_rejects_invalid_name_or_status(payload):
    with pytest.raises(ValidationError):
        MenuCreate(**payload)


def test_menu_item_rejects_negative_price():
    with pytest.raises(ValidationError):
        MenuItemInput(
            recipe_id=uuid4(),
            display_name="House Martini",
            selling_price_vnd=-1,
        )
