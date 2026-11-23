from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bom import BomTemplate, BomTemplateItem
from app.models.part import Part
from app.schemas.bom import (
    BomItemCreate,
    BomItemUpdate,
    BomPreviewItem,
    BomTemplateCreate,
    BomTemplateUpdate,
)


async def list_templates(
    db: AsyncSession, *, include_inactive: bool = False, q: str | None = None
) -> list[BomTemplate]:
    stmt = select(BomTemplate).options(selectinload(BomTemplate.items)).order_by(BomTemplate.name)
    if not include_inactive:
        stmt = stmt.where(BomTemplate.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(BomTemplate.name.ilike(pattern) | BomTemplate.code.ilike(pattern))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_template_or_404(db: AsyncSession, template_id: UUID) -> BomTemplate:
    stmt = (
        select(BomTemplate)
        .options(selectinload(BomTemplate.items))
        .where(BomTemplate.id == template_id)
    )
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон BOM не найден")
    return template


async def create_template(db: AsyncSession, payload: BomTemplateCreate) -> BomTemplate:
    existing = await db.execute(select(BomTemplate).where(BomTemplate.code == payload.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Шаблон BOM с кодом '{payload.code}' уже существует",
        )
    template = BomTemplate(**payload.model_dump())
    db.add(template)
    await db.commit()
    return await get_template_or_404(db, template.id)


async def update_template(
    db: AsyncSession, template_id: UUID, payload: BomTemplateUpdate
) -> BomTemplate:
    template = await get_template_or_404(db, template_id)
    data = payload.model_dump(exclude_unset=True)

    if "code" in data and data["code"] != template.code:
        existing = await db.execute(select(BomTemplate).where(BomTemplate.code == data["code"]))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Шаблон BOM с кодом '{data['code']}' уже существует",
            )

    for key, value in data.items():
        setattr(template, key, value)

    await db.commit()
    return await get_template_or_404(db, template.id)


async def delete_template(db: AsyncSession, template_id: UUID) -> None:
    template = await get_template_or_404(db, template_id)
    await db.delete(template)
    await db.commit()


async def add_template_item(
    db: AsyncSession, template_id: UUID, payload: BomItemCreate
) -> BomTemplateItem:
    await get_template_or_404(db, template_id)

    part_res = await db.execute(select(Part).where(Part.id == payload.part_id))
    part = part_res.scalar_one_or_none()
    if part is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запчасть не найдена")

    dup_res = await db.execute(
        select(BomTemplateItem).where(
            BomTemplateItem.template_id == template_id,
            BomTemplateItem.part_id == payload.part_id,
        )
    )
    if dup_res.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Эта запчасть уже добавлена в шаблон BOM",
        )

    item = BomTemplateItem(template_id=template_id, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_template_item(
    db: AsyncSession, template_id: UUID, item_id: UUID, payload: BomItemUpdate
) -> BomTemplateItem:
    res = await db.execute(
        select(BomTemplateItem).where(
            BomTemplateItem.id == item_id,
            BomTemplateItem.template_id == template_id,
        )
    )
    item = res.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Позиция шаблона BOM не найдена"
        )

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return item


async def remove_template_item(db: AsyncSession, template_id: UUID, item_id: UUID) -> None:
    res = await db.execute(
        select(BomTemplateItem).where(
            BomTemplateItem.id == item_id,
            BomTemplateItem.template_id == template_id,
        )
    )
    item = res.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Позиция шаблона BOM не найдена"
        )
    await db.delete(item)
    await db.commit()


async def preview_template(
    db: AsyncSession, template_id: UUID, multiplier: int = 1
) -> list[BomPreviewItem]:
    await get_template_or_404(db, template_id)
    stmt = (
        select(BomTemplateItem, Part)
        .join(Part, BomTemplateItem.part_id == Part.id)
        .where(BomTemplateItem.template_id == template_id)
        .order_by(Part.name)
    )
    result = await db.execute(stmt)
    preview: list[BomPreviewItem] = []
    for item, part in result.all():
        total_qty = Decimal(str(item.quantity)) * Decimal(multiplier)
        preview.append(
            BomPreviewItem(
                part_id=part.id,
                sku=part.sku,
                name=part.name,
                unit=part.unit,
                quantity=total_qty,
                is_optional=item.is_optional,
            )
        )
    return preview
