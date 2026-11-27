import csv
import io
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part import Part
from app.schemas.part import PartCreate, PartImportResult, PartUpdate


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


async def import_parts_csv(db: AsyncSession, raw_bytes: bytes) -> PartImportResult:
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Файл должен быть в кодировке UTF-8",
        ) from exc

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CSV-файл пуст",
        )

    delimiter = ";" if ";" in lines[0] and "," not in lines[0] else ","
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter)
    if not reader.fieldnames or not {"sku", "name"}.issubset(
        {f.strip().lower() for f in reader.fieldnames}
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "CSV должен содержать обязательные колонки: sku, name (опционально: unit, category)"
            ),
        )

    existing_res = await db.execute(select(Part.sku))
    known_skus: set[str] = set(existing_res.scalars().all())

    created = 0
    skipped = 0
    errors: list[str] = []

    for row_num, raw_row in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw_row.items()}
        sku = row.get("sku", "")
        name = row.get("name", "")
        unit = row.get("unit") or "шт"
        category = row.get("category") or None

        if not sku or not name:
            errors.append(f"Строка {row_num}: пустой sku или name")
            continue

        if sku in known_skus:
            skipped += 1
            continue

        try:
            validated = PartCreate(sku=sku, name=name, unit=unit, category=category)
        except Exception as exc:
            errors.append(f"Строка {row_num} ({sku}): {exc}")
            continue

        db.add(Part(**validated.model_dump()))
        known_skus.add(sku)
        created += 1

    if created > 0:
        await db.commit()

    return PartImportResult(created=created, skipped=skipped, errors=errors)
