import pytest
from pydantic import ValidationError

from app.schemas.part import PartCreate, PartUpdate


def test_part_create_defaults():
    part = PartCreate(sku="MOT-2212", name="Бесколлекторный мотор 2212")
    assert part.unit == "шт"
    assert part.is_active is True
    assert part.category is None


def test_part_create_invalid_sku():
    with pytest.raises(ValidationError):
        PartCreate(sku="", name="Мотор")

    with pytest.raises(ValidationError):
        PartCreate(sku="A" * 65, name="Мотор")


def test_part_update_partial():
    upd = PartUpdate(name="Новое название")
    data = upd.model_dump(exclude_unset=True)
    assert data == {"name": "Новое название"}
