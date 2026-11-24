from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate, OrderUpdate
from app.utils.order_number import generate_order_number

# Сколько раз пробуем выдать номер, если параллельный запрос успел занять такой же.
NUMBER_ATTEMPTS = 3


async def list_orders(
    db: AsyncSession,
    *,
    order_status: OrderStatus | None = None,
    customer_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Order]:
    stmt = select(Order)
    if order_status is not None:
        stmt = stmt.where(Order.status == order_status)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)
    # Сначала новые. Номер вторым ключом: created_at у заказов из одной секунды совпадает.
    stmt = stmt.order_by(Order.created_at.desc(), Order.number.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_order_or_404(db: AsyncSession, order_id: UUID) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return order


async def _ensure_customer_exists(db: AsyncSession, customer_id: UUID) -> None:
    if await db.get(Customer, customer_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказчик не найден")


async def create_order(db: AsyncSession, payload: OrderCreate) -> Order:
    """Создаёт заказ в статусе draft и выдаёт ему номер ORD-YYYY-NNNNN.

    Два параллельных запроса могут подобрать один и тот же номер. Тогда `flush` второго
    падает на уникальном индексе `orders.number`: откатываем транзакцию и пробуем снова.
    """
    await _ensure_customer_exists(db, payload.customer_id)

    for _ in range(NUMBER_ATTEMPTS):
        order = Order(
            number=await generate_order_number(db),
            status=OrderStatus.draft,
            **payload.model_dump(),
        )
        db.add(order)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            continue
        await db.refresh(order)
        return order

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Не удалось выдать номер заказа, повторите запрос",
    )


async def update_order(db: AsyncSession, order_id: UUID, payload: OrderUpdate) -> Order:
    """Меняет срок, описание или заказчика. Разрешено только для заказа в статусе draft."""
    order = await get_order_or_404(db, order_id)
    if order.status != OrderStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Редактировать можно только заказ в статусе draft, сейчас: {order.status}",
        )

    data = payload.model_dump(exclude_unset=True)
    if "customer_id" in data:
        await _ensure_customer_exists(db, data["customer_id"])

    for key, value in data.items():
        setattr(order, key, value)
    await db.flush()
    await db.refresh(order)
    return order
