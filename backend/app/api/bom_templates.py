from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.bom import (
    BomItemCreate,
    BomItemRead,
    BomItemUpdate,
    BomPreviewItem,
    BomTemplateCreate,
    BomTemplateRead,
    BomTemplateUpdate,
)
from app.services import bom_service

router = APIRouter(prefix="/bom-templates", tags=["bom"])

ManagerUser = Annotated[User, Depends(require_roles(UserRole.manager))]
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[BomTemplateRead], summary="Список шаблонов BOM")
async def list_templates(
    db: DbSession,
    _user: CurrentUser,
    include_inactive: bool = Query(default=False),
    q: str | None = Query(default=None),
) -> list[BomTemplateRead]:
    items = await bom_service.list_templates(db, include_inactive=include_inactive, q=q)
    return [BomTemplateRead.model_validate(item) for item in items]


@router.post(
    "", response_model=BomTemplateRead, status_code=status.HTTP_201_CREATED, summary="Создать BOM"
)
async def create_template(
    payload: BomTemplateCreate, db: DbSession, _user: ManagerUser
) -> BomTemplateRead:
    template = await bom_service.create_template(db, payload)
    return BomTemplateRead.model_validate(template)


@router.get("/{template_id}", response_model=BomTemplateRead, summary="Получить шаблон BOM")
async def get_template(template_id: UUID, db: DbSession, _user: CurrentUser) -> BomTemplateRead:
    template = await bom_service.get_template_or_404(db, template_id)
    return BomTemplateRead.model_validate(template)


@router.patch("/{template_id}", response_model=BomTemplateRead, summary="Обновить шаблон BOM")
async def update_template(
    template_id: UUID, payload: BomTemplateUpdate, db: DbSession, _user: ManagerUser
) -> BomTemplateRead:
    template = await bom_service.update_template(db, template_id, payload)
    return BomTemplateRead.model_validate(template)


@router.delete(
    "/{template_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить шаблон BOM"
)
async def delete_template(template_id: UUID, db: DbSession, _user: ManagerUser) -> None:
    await bom_service.delete_template(db, template_id)


@router.post(
    "/{template_id}/items",
    response_model=BomItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить позицию в шаблон BOM",
)
async def add_template_item(
    template_id: UUID, payload: BomItemCreate, db: DbSession, _user: ManagerUser
) -> BomItemRead:
    item = await bom_service.add_template_item(db, template_id, payload)
    return BomItemRead.model_validate(item)


@router.patch(
    "/{template_id}/items/{item_id}",
    response_model=BomItemRead,
    summary="Обновить позицию шаблона BOM",
)
async def update_template_item(
    template_id: UUID, item_id: UUID, payload: BomItemUpdate, db: DbSession, _user: ManagerUser
) -> BomItemRead:
    item = await bom_service.update_template_item(db, template_id, item_id, payload)
    return BomItemRead.model_validate(item)


@router.delete(
    "/{template_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить позицию из шаблона BOM",
)
async def remove_template_item(
    template_id: UUID, item_id: UUID, db: DbSession, _user: ManagerUser
) -> None:
    await bom_service.remove_template_item(db, template_id, item_id)


@router.get(
    "/{template_id}/preview",
    response_model=list[BomPreviewItem],
    summary="Предпросмотр состава BOM (sku, name, quantity)",
)
async def preview_template(
    template_id: UUID,
    db: DbSession,
    _user: CurrentUser,
    quantity: int = Query(default=1, ge=1, description="Количество комплектов/изделий"),
) -> list[BomPreviewItem]:
    return await bom_service.preview_template(db, template_id, multiplier=quantity)
