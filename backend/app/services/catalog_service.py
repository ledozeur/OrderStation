from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part import Part
from app.schemas.part import PartCreate, PartUpdate


async def list_parts(
    db: AsyncSession,
    *,
    include_inactive: bool = False,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Part]:
    stmt = select(Part).order_by(Part.name)
    if not include_inactive:
        stmt = stmt.where(Part.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(Part.name.ilike(pattern) | Part.sku.ilike(pattern))
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_part_or_404(db: AsyncSession, part_id: UUID) -> Part:
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if part is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запчасть не найдена")
    return part


async def create_part(db: AsyncSession, payload: PartCreate) -> Part:
    existing = await db.execute(select(Part).where(Part.sku == payload.sku))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Запчасть с артикулом '{payload.sku}' уже существует",
        )
    part = Part(**payload.model_dump())
    db.add(part)
    await db.commit()
    await db.refresh(part)
    return part


async def update_part(db: AsyncSession, part_id: UUID, payload: PartUpdate) -> Part:
    part = await get_part_or_404(db, part_id)
    data = payload.model_dump(exclude_unset=True)

    if "sku" in data and data["sku"] != part.sku:
        existing = await db.execute(select(Part).where(Part.sku == data["sku"]))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Запчасть с артикулом '{data['sku']}' уже существует",
            )

    for key, value in data.items():
        setattr(part, key, value)

    await db.commit()
    await db.refresh(part)
    return part


async def soft_delete_part(db: AsyncSession, part_id: UUID) -> None:
    part = await get_part_or_404(db, part_id)
    part.is_active = False
    await db.commit()
