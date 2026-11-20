import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderType(enum.StrEnum):
    standard = "standard"
    custom = "custom"


class OrderStatus(enum.StrEnum):
    draft = "draft"
    confirmed = "confirmed"
    in_procurement = "in_procurement"
    completed = "completed"
    cancelled = "cancelled"


class OrderLineSource(enum.StrEnum):
    template = "template"
    manual = "manual"


class ProcurementStatus(enum.StrEnum):
    not_ordered = "not_ordered"
    ordered = "ordered"
    in_transit = "in_transit"
    received = "received"
    cancelled = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT")
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("bom_templates.id", ondelete="SET NULL"), nullable=True
    )
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), default=OrderType.custom)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.draft)
    deadline_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id", ondelete="CASCADE"))
    part_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("parts.id", ondelete="RESTRICT"))
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=1)
    source: Mapped[OrderLineSource] = mapped_column(
        Enum(OrderLineSource), default=OrderLineSource.manual
    )
    procurement_status: Mapped[ProcurementStatus] = mapped_column(
        Enum(ProcurementStatus), default=ProcurementStatus.not_ordered
    )
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[Order] = relationship(back_populates="lines")
