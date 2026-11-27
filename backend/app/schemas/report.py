from uuid import UUID

from pydantic import BaseModel, Field

from app.models.order import ProcurementStatus


class ProcurementSummaryRead(BaseModel):
    """Сводка закупки по заказу."""

    order_id: UUID
    total_lines: int = Field(description="Сколько всего позиций в заказе.")
    by_status: dict[ProcurementStatus, int] = Field(
        description="Количество позиций по каждому статусу закупки (нулевые тоже указаны).",
        examples=[{"not_ordered": 2, "ordered": 5, "in_transit": 0, "received": 3, "cancelled": 0}],
    )
    percent_received: float = Field(
        description=(
            "Доля позиций в статусе received от всех позиций заказа (включая cancelled), "
            "в процентах, округлена до 0.1. Для заказа без позиций — 0.0."
        ),
        examples=[30.0],
    )
