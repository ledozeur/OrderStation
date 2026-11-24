from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import OrderLine, ProcurementStatus

ALLOWED_PROCUREMENT_TRANSITIONS: dict[ProcurementStatus, set[ProcurementStatus]] = {
    ProcurementStatus.not_ordered: {
        ProcurementStatus.ordered,
        ProcurementStatus.cancelled,
    },
    ProcurementStatus.ordered: {
        ProcurementStatus.in_transit,
        ProcurementStatus.cancelled,
    },
    ProcurementStatus.in_transit: {
        ProcurementStatus.received,
        ProcurementStatus.cancelled,
    },
    ProcurementStatus.received: set(),
    ProcurementStatus.cancelled: set(),
}


def validate_procurement_transition(
        current_status: ProcurementStatus, new_status: ProcurementStatus
) -> None:
    if current_status == new_status:
        return
    allowed = ALLOWED_PROCUREMENT_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Недопустимый переход статуса закупки: "
                f"'{current_status.value}' -> '{new_status.value}'"
            ),
        )


async def get_order_line_or_404(
        db: AsyncSession, order_id: UUID, line_id: UUID
) -> OrderLine:
    stmt = select(OrderLine).where(
        OrderLine.id == line_id,
        OrderLine.order_id == order_id,
        )
    result = await db.execute(stmt)
    line = result.scalar_one_or_none()
    if line is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Позиция заказа не найдена",
        )
    return line


async def update_line_procurement(
        db: AsyncSession,
        order_id: UUID,
        line_id: UUID,
        *,
        procurement_status: ProcurementStatus | None = None,
        supplier_name: str | None = None,
        expected_delivery_date: date | None = None,
        actual_delivery_date: date | None = None,
        note: str | None = None,
        fields_set: set[str] | None = None,
) -> OrderLine:
    line = await get_order_line_or_404(db, order_id, line_id)
    updated_fields = fields_set or set()

    if procurement_status is not None:
        validate_procurement_transition(line.procurement_status, procurement_status)
        if (
                procurement_status == ProcurementStatus.ordered
                and line.procurement_status != ProcurementStatus.ordered
                and line.ordered_at is None
        ):
            line.ordered_at = datetime.now(UTC)
        if (
                procurement_status == ProcurementStatus.received
                and line.procurement_status != ProcurementStatus.received
                and actual_delivery_date is None
                and line.actual_delivery_date is None
        ):
            line.actual_delivery_date = datetime.now(UTC).date()
        line.procurement_status = procurement_status

    new_expected = (
        expected_delivery_date
        if ("expected_delivery_date" in updated_fields or expected_delivery_date is not None)
        else line.expected_delivery_date
    )
    if new_expected is not None and line.ordered_at is not None:
        if new_expected < line.ordered_at.date():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ожидаемая дата доставки не может быть раньше даты заказа (ordered_at)",
            )

    if "supplier_name" in updated_fields or supplier_name is not None:
        line.supplier_name = supplier_name
    if "expected_delivery_date" in updated_fields or expected_delivery_date is not None:
        line.expected_delivery_date = expected_delivery_date
    if "actual_delivery_date" in updated_fields or actual_delivery_date is not None:
        line.actual_delivery_date = actual_delivery_date
    if "note" in updated_fields or note is not None:
        line.note = note

    await db.commit()
    await db.refresh(line)
    return line
