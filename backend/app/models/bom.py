import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BomTemplate(Base):
    __tablename__ = "bom_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    product_line: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    items: Mapped[list["BomTemplateItem"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class BomTemplateItem(Base):
    __tablename__ = "bom_template_items"
    __table_args__ = (UniqueConstraint("template_id", "part_id", name="uq_template_part"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bom_templates.id", ondelete="CASCADE")
    )
    part_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("parts.id", ondelete="RESTRICT"))
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=1)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    template: Mapped[BomTemplate] = relationship(back_populates="items")