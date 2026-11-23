from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_person: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    notes: str | None = None


class CustomerCreate(CustomerBase):
    # пробелы по краям обрезаются до проверки min_length, поэтому name="   " даёт 422.
    model_config = ConfigDict(str_strip_whitespace=True)


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_person: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_null(cls, value: str | None) -> str | None:
        # поле можно не передавать вовсе, но явный null недопустим: name в бд обязательное
        if value is None:
            raise ValueError("name не может быть null")
        return value


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
