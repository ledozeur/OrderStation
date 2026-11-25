from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_roles
from app.models.order import Order, OrderStatus
from app.schemas.order import (
    ApplyTemplateRequest,
    OrderCreate,
    OrderRead,
    OrderUpdate,
    OrderWithLinesRead,
)
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])

ManagerUser = Annotated[object, Depends(require_roles("manager"))]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "",
    response_model=list[OrderRead],
    summary="Реестр заказов",
    description=(
        "Возвращает заказы постранично, сначала новые. "
        "Можно отфильтровать по статусу (`status`) и заказчику (`customer_id`)."
    ),
)
async def list_orders(
    _: CurrentUser,
    db: DbSession,
    order_status: Annotated[
        OrderStatus | None,
        Query(
            alias="status",
            description="Только заказы в этом статусе: draft, confirmed, in_procurement, "
            "completed, cancelled.",
        ),
    ] = None,
    customer_id: Annotated[UUID | None, Query(description="Только заказы этого заказчика.")] = None,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Сколько записей вернуть (от 1 до 100).")
    ] = 50,
    offset: Annotated[
        int, Query(ge=0, description="Сколько записей пропустить с начала списка.")
    ] = 0,
) -> list[Order]:
    return await order_service.list_orders(
        db, order_status=order_status, customer_id=customer_id, limit=limit, offset=offset
    )


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заказ",
    description="Создаёт заказ в статусе `draft` и выдаёт ему номер вида ORD-2026-00042.",
    responses={
        404: {"description": "Заказчик не найден"},
        409: {"description": "Не удалось выдать уникальный номер заказа"},
    },
)
async def create_order(_: ManagerUser, db: DbSession, body: OrderCreate) -> Order:
    return await order_service.create_order(db, body)


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    summary="Получить заказ по ID",
    responses={404: {"description": "Заказ не найден"}},
)
async def get_order(_: CurrentUser, db: DbSession, order_id: UUID) -> Order:
    return await order_service.get_order_or_404(db, order_id)


@router.patch(
    "/{order_id}",
    response_model=OrderRead,
    summary="Изменить заказ (только draft)",
    description="Меняет срок, описание или заказчика. Заказ не в статусе `draft` изменить нельзя.",
    responses={
        404: {"description": "Заказ или заказчик не найден"},
        409: {"description": "Заказ не в статусе draft"},
    },
)
async def update_order(_: ManagerUser, db: DbSession, order_id: UUID, body: OrderUpdate) -> Order:
    return await order_service.update_order(db, order_id, body)


@router.post(
    "/{order_id}/apply-template",
    response_model=OrderWithLinesRead,
    # остальные параметры без изменений
)
async def apply_template(
    _: ManagerUser, db: DbSession, order_id: UUID, body: ApplyTemplateRequest
) -> Order:
    order = await order_service.apply_template(db, order_id, body.template_id)
    # В async-сессии связь lines не подгружается сама: без этого будет MissingGreenlet.
    await db.refresh(order, ["lines"])
    return order
