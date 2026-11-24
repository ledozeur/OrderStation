from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.order import OrderStatus, OrderType


class OrderCreate(BaseModel):
    """Создание заказа. Номер и статус `draft` назначает сервер."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: UUID = Field(description="ID заказчика.")
    deadline_date: date | None = Field(
        default=None, description="Срок выполнения заказа (ГГГГ-ММ-ДД).", examples=["2026-12-31"]
    )
    description: str | None = Field(default=None, description="Описание заказа.")


class OrderUpdate(BaseModel):
    """Изменение заказа. Работает только для заказа в статусе `draft`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: UUID | None = Field(default=None, description="Новый заказчик.")
    deadline_date: date | None = Field(
        default=None,
        description="Новый срок (ГГГГ-ММ-ДД). Явный `null` убирает срок.",
        examples=["2026-12-31"],
    )
    description: str | None = Field(
        default=None, description="Новое описание. Явный `null` очищает описание."
    )

    @field_validator("customer_id")
    @classmethod
    def customer_id_must_not_be_null(cls, value: UUID | None) -> UUID | None:
        # Поле можно не передавать вовсе, но явный null недопустим: заказчик обязателен.
        if value is None:
            raise ValueError("customer_id не может быть null")
        return value


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str = Field(description="Номер заказа вида ORD-2026-00042.")
    customer_id: UUID
    template_id: UUID | None = Field(
        description="Шаблон BOM, применённый к заказу (заполняется при apply-template)."
    )
    order_type: OrderType
    status: OrderStatus
    deadline_date: date | None
    description: str | None
    created_at: datetime
    confirmed_at: datetime | None
