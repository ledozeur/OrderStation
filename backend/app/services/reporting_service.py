from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderLine, OrderStatus, ProcurementStatus
from app.schemas.report import ProcurementSummaryRead

# Заказы в этих статусах уже закрыты: срок у них не «горит» и просроченными они не считаются.
CLOSED_STATUSES = (OrderStatus.completed, OrderStatus.cancelled)


def overdue_clause(today: date) -> ColumnElement[bool]:
    """Условие просрочки: срок раньше `today`, заказ не completed/cancelled.

    Вынесено отдельно, чтобы `GET /orders?overdue=true` (K-W3-02) использовал ту же логику.
    Заказ без срока (NULL) просроченным не считается.
    """
    return and_(
        Order.deadline_date.is_not(None),
        Order.deadline_date < today,
        Order.status.not_in(CLOSED_STATUSES),
    )


async def list_deadline_orders(
    db: AsyncSession,
    *,
    due_in_days: int | None = None,
    overdue: bool = False,
    today: date | None = None,
) -> list[Order]:
    """Заказы, у которых срок требует внимания. Всегда только открытые заказы со сроком.

    - ``overdue=True`` — просроченные (срок раньше сегодняшнего дня);
    - ``due_in_days=N`` — срок в интервале [сегодня, сегодня + N] включительно;
    - оба параметра — объединение (просроченные ИЛИ срок в ближайшие N дней);
    - ни одного — все открытые заказы со сроком.

    Сначала самые ранние сроки. Параметр ``today`` нужен для тестов.
    """
    today = today or date.today()

    stmt = select(Order).where(
        Order.deadline_date.is_not(None),
        Order.status.not_in(CLOSED_STATUSES),
    )

    conditions: list[ColumnElement[bool]] = []
    if overdue:
        conditions.append(overdue_clause(today))
    if due_in_days is not None:
        conditions.append(Order.deadline_date.between(today, today + timedelta(days=due_in_days)))
    if conditions:
        stmt = stmt.where(or_(*conditions))

    stmt = stmt.order_by(Order.deadline_date.asc(), Order.number.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_procurement_summary(db: AsyncSession, order_id: UUID) -> ProcurementSummaryRead:
    """Сводка закупки по заказу: счётчики по статусам и процент полученных позиций.

    В `by_status` всегда все статусы (нулевые тоже). `cancelled` входит в `total_lines`
    и, значит, в знаменатель `percent_received`. Заказ без позиций даёт 0.0, а не деление на ноль.
    """
    # Проверяем заказ напрямую, а не через order_service: тот будет импортировать
    # reporting_service (K-W3-02), и получился бы циклический импорт.
    if await db.get(Order, order_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")

    rows = await db.execute(
        select(OrderLine.procurement_status, func.count())
        .where(OrderLine.order_id == order_id)
        .group_by(OrderLine.procurement_status)
    )
    by_status = {s: 0 for s in ProcurementStatus}
    for line_status, count in rows.all():
        by_status[line_status] = count

    total = sum(by_status.values())
    received = by_status[ProcurementStatus.received]
    percent = round(received / total * 100, 1) if total else 0.0

    return ProcurementSummaryRead(
        order_id=order_id, total_lines=total, by_status=by_status, percent_received=percent
    )
