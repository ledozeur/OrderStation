from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_roles
from app.models.user import User, UserRole
from app.schemas.procurement import (
    OrderLineProcurementRead,
    OrderLineRead,
    ProcurementBulkItem,
    ProcurementUpdate,
)
from app.services import procurement_service

router = APIRouter(prefix="/orders", tags=["procurement"])

ProcurementUser = Annotated[User, Depends(require_roles(UserRole.procurement, UserRole.manager))]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/{order_id}/lines",
    response_model=list[OrderLineRead],
    summary="Список позиций заказа с артикулом и названием запчасти",
    responses={404: {"description": "Заказ не найден"}},
)
async def get_order_lines(
    order_id: UUID,
    db: DbSession,
    _user: CurrentUser,
) -> list[OrderLineRead]:
    return await procurement_service.list_order_lines(db, order_id)


@router.patch(
    "/{order_id}/lines/procurement-bulk",
    response_model=list[OrderLineProcurementRead],
    summary="Массовое обновление закупки по позициям заказа (до 50 линий)",
    responses={
        404: {"description": "Заказ или позиция не найдены"},
        409: {"description": "Недопустимый переход статуса"},
        422: {"description": "Ошибка валидации (больше 50 элементов или неверная дата)"},
    },
)
async def patch_lines_procurement_bulk(
    order_id: UUID,
    payload: Annotated[list[ProcurementBulkItem], Body(min_length=1, max_length=50)],
    db: DbSession,
    _user: ProcurementUser,
) -> list[OrderLineProcurementRead]:
    lines = await procurement_service.bulk_update_line_procurement(db, order_id, payload)
    return [OrderLineProcurementRead.model_validate(line) for line in lines]


@router.patch(
    "/{order_id}/lines/{line_id}/procurement",
    response_model=OrderLineProcurementRead,
    summary="Обновить статус и данные закупки по позиции заказа",
)
async def patch_line_procurement(
    order_id: UUID,
    line_id: UUID,
    payload: ProcurementUpdate,
    db: DbSession,
    _user: ProcurementUser,
) -> OrderLineProcurementRead:
    line = await procurement_service.update_line_procurement(
        db,
        order_id,
        line_id,
        procurement_status=payload.procurement_status,
        supplier_name=payload.supplier_name,
        expected_delivery_date=payload.expected_delivery_date,
        actual_delivery_date=payload.actual_delivery_date,
        note=payload.note,
        fields_set=payload.model_fields_set,
    )
    return OrderLineProcurementRead.model_validate(line)
