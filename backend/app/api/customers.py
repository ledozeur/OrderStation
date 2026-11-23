from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_roles
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])

# Символ, которым экранируются служебные знаки LIKE (%, _) в строке поиска.
LIKE_ESCAPE = "/"


def _like_pattern(text: str) -> str:
    """Шаблон «содержит подстроку» для LIKE: %, _ и сам символ экранирования ищутся буквально."""
    escaped = text.replace("/", "//").replace("%", "/%").replace("_", "/_")
    return f"%{escaped}%"


@router.get(
    "",
    response_model=list[CustomerRead],
    summary="Список заказчиков",
    description=(
        "Возвращает заказчиков постранично. Поддерживает поиск по названию (`q`) "
        "и сортировку по названию (`sort`)."
    ),
)
async def list_customers(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[
        str | None,
        Query(
            max_length=255,
            description=(
                "Поиск по названию заказчика: подстрока без учёта регистра. "
                "Пустая строка или одни пробелы — поиск не применяется."
            ),
        ),
    ] = None,
    sort: Annotated[
        Literal["name", "-name"],
        Query(
            description=(
                "Сортировка по названию: `name` — по возрастанию (по умолчанию), "
                "`-name` — по убыванию."
            ),
        ),
    ] = "name",
    limit: Annotated[
        int, Query(ge=1, le=100, description="Сколько записей вернуть (от 1 до 100).")
    ] = 50,
    offset: Annotated[
        int, Query(ge=0, description="Сколько записей пропустить с начала списка.")
    ] = 0,
) -> list[Customer]:
    stmt = select(Customer)

    search = q.strip() if q else ""
    if search:
        stmt = stmt.where(Customer.name.ilike(_like_pattern(search), escape=LIKE_ESCAPE))

    name_order = Customer.name.desc() if sort == "-name" else Customer.name.asc()
    # id — вторым ключом: при одинаковых названиях порядок и пагинация остаются стабильными.
    stmt = stmt.order_by(name_order, Customer.id).offset(offset).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заказчика",
)
async def create_customer(
    _: Annotated[object, Depends(require_roles("manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: CustomerCreate,
) -> Customer:
    customer = Customer(**body.model_dump())
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerRead, summary="Получить заказчика по ID")
async def get_customer(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    customer_id: UUID,
) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказчик не найден")
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead, summary="Обновить заказчика")
async def update_customer(
    _: Annotated[object, Depends(require_roles("manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    customer_id: UUID,
    body: CustomerUpdate,
) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказчик не найден")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.delete(
    "/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить заказчика"
)
async def delete_customer(
    _: Annotated[object, Depends(require_roles("manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    customer_id: UUID,
) -> None:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказчик не найден")
    await db.delete(customer)
