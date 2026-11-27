from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.order import Order
from app.schemas.order import OrderRead
from app.schemas.report import ProcurementSummaryRead
from app.services import reporting_service

router = APIRouter(prefix="/reports", tags=["reports"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/deadlines",
    response_model=list[OrderRead],
    summary="Отчёт по срокам заказов",
    description=(
        "Открытые заказы (не `completed` и не `cancelled`) со сроком выполнения, "
        "сначала самые ранние сроки. Заказы без срока не попадают в отчёт. "
        "`overdue=true` — только просроченные (срок раньше сегодняшнего дня). "
        "`due_in_days=N` — срок в интервале от сегодня до сегодня + N дней включительно. "
        "Если переданы оба параметра, возвращаются заказы, подходящие под любой из них. "
        "Без параметров — все открытые заказы со сроком."
    ),
)
async def deadlines_report(
    _: CurrentUser,
    db: DbSession,
    due_in_days: Annotated[
        int | None,
        Query(ge=0, le=3650, description="Срок наступает в ближайшие N дней (включая сегодня)."),
    ] = None,
    overdue: Annotated[bool, Query(description="Только просроченные заказы.")] = False,
) -> list[Order]:
    return await reporting_service.list_deadline_orders(
        db, due_in_days=due_in_days, overdue=overdue
    )


@router.get(
    "/orders/{order_id}/procurement-summary",
    response_model=ProcurementSummaryRead,
    summary="Сводка закупки по заказу",
    description=(
        "Сколько позиций заказа в каждом статусе закупки и какая доля получена. "
        "`percent_received` считается от всех позиций заказа, включая отменённые. "
        "Для заказа без позиций — 0.0."
    ),
    responses={404: {"description": "Заказ не найден"}},
)
async def procurement_summary(
    _: CurrentUser, db: DbSession, order_id: UUID
) -> ProcurementSummaryRead:
    return await reporting_service.get_procurement_summary(db, order_id)
