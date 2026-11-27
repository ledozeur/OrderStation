from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import ProcurementStatus


class ProcurementUpdate(BaseModel):
    procurement_status: ProcurementStatus | None = None
    supplier_name: str | None = Field(default=None, max_length=255)
    expected_delivery_date: date | None = None
    actual_delivery_date: date | None = None
    note: str | None = None


class ProcurementBulkItem(ProcurementUpdate):
    line_id: UUID


class OrderLineProcurementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    part_id: UUID
    quantity: Decimal
    procurement_status: ProcurementStatus
    supplier_name: str | None
    ordered_at: datetime | None
    expected_delivery_date: date | None
    actual_delivery_date: date | None
    note: str | None


class OrderLineRead(OrderLineProcurementRead):
    source: str = Field(examples=["template"])
    part_sku: str = Field(examples=["UAV-MOT-2216"])
    part_name: str = Field(examples=["Двигатель бесколлекторный 2216 920KV"])
