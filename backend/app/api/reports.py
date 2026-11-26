from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.order import Order
from app.schemas.order import OrderRead
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