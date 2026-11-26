from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_roles
from app.models.user import User, UserRole
from app.schemas.procurement import (
    OrderLineProcurementRead,
    OrderLineRead,
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
