from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PartBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64, examples=["FRAME-X500"])
    name: str = Field(min_length=1, max_length=255, examples=["Рама карбоновая X500"])
    unit: str = Field(default="шт", min_length=1, max_length=32, examples=["шт"])
    category: str | None = Field(default=None, max_length=128, examples=["Рамы"])
    is_active: bool = True


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    category: str | None = Field(default=None, max_length=128)
    is_active: bool | None = None


class PartRead(PartBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
