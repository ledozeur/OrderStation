from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BomTemplateBase(BaseModel):
    code: str = Field(min_length=1, max_length=64, examples=["UAV-X500-V1"])
    name: str = Field(min_length=1, max_length=255, examples=["Квадрокоптер X500 (базовый)"])
    product_line: str | None = Field(default=None, max_length=128, examples=["X-Series"])
    version: str = Field(default="1.0", min_length=1, max_length=32, examples=["1.0"])
    is_active: bool = True


class BomTemplateCreate(BomTemplateBase):
    pass


class BomTemplateUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    product_line: str | None = Field(default=None, max_length=128)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    is_active: bool | None = None


class BomItemCreate(BaseModel):
    part_id: UUID
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    is_optional: bool = False
    note: str | None = None


class BomItemUpdate(BaseModel):
    quantity: Decimal | None = Field(default=None, gt=0)
    is_optional: bool | None = None
    note: str | None = None


class BomItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    part_id: UUID
    quantity: Decimal
    is_optional: bool
    note: str | None


class BomTemplateRead(BomTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    items: list[BomItemRead] = []


class BomPreviewItem(BaseModel):
    part_id: UUID
    sku: str
    name: str
    unit: str
    quantity: Decimal
    is_optional: bool
