from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.part import PartCreate, PartRead, PartUpdate
from app.services import catalog_service

router = APIRouter(prefix="/parts", tags=["parts"])


ManagerUser = Annotated[User, Depends(require_roles(UserRole.manager))]
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[PartRead], summary="Список запчастей")
async def list_parts(
    db: DbSession,
    _user: CurrentUser,
    include_inactive: bool = Query(default=False, description="Включать архивные (неактивные)"),
    q: str | None = Query(default=None, description="Поиск по артикулу или названию"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PartRead]:
    items = await catalog_service.list_parts(
        db, include_inactive=include_inactive, q=q, limit=limit, offset=offset
    )
    return [PartRead.model_validate(item) for item in items]


@router.post(
    "", response_model=PartRead, status_code=status.HTTP_201_CREATED, summary="Создать запчасть"
)
async def create_part(payload: PartCreate, db: DbSession, _user: ManagerUser) -> PartRead:
    part = await catalog_service.create_part(db, payload)
    return PartRead.model_validate(part)


@router.get("/{part_id}", response_model=PartRead, summary="Получить запчасть по ID")
async def get_part(part_id: UUID, db: DbSession, _user: CurrentUser) -> PartRead:
    part = await catalog_service.get_part_or_404(db, part_id)
    return PartRead.model_validate(part)


@router.patch("/{part_id}", response_model=PartRead, summary="Обновить запчасть")
async def update_part(
    part_id: UUID, payload: PartUpdate, db: DbSession, _user: ManagerUser
) -> PartRead:
    part = await catalog_service.update_part(db, part_id, payload)
    return PartRead.model_validate(part)


@router.delete(
    "/{part_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Архивировать запчасть (soft delete)",
)
async def delete_part(part_id: UUID, db: DbSession, _user: ManagerUser) -> None:
    await catalog_service.soft_delete_part(db, part_id)
