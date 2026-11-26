from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.order import (
    Order,
    OrderLine,
    OrderLineSource,
    OrderStatus,
    OrderType,
    ProcurementStatus,
)
from app.schemas.order import OrderCreate, OrderUpdate
from app.services import bom_service
from app.services.reporting_service import overdue_clause
from app.utils.order_number import generate_order_number

# Сколько раз пробуем выдать номер, если параллельный запрос успел занять такой же.
NUMBER_ATTEMPTS = 3


async def list_orders(
    db: AsyncSession,
    *,
    order_status: OrderStatus | None = None,
    customer_id: UUID | None = None,
    overdue: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Order]:
    stmt = select(Order)
    if order_status is not None:
        stmt = stmt.where(Order.status == order_status)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)
    if overdue:
        # Тот же критерий, что в отчёте /reports/deadlines (K-W3-01).
        stmt = stmt.where(overdue_clause(date.today()))
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


async def apply_template(db: AsyncSession, order_id: UUID, template_id: UUID) -> Order:
    """Копирует позиции шаблона BOM в строки заказа (source=template). Только для draft.

    Что копируется: каждая позиция шаблона становится строкой заказа с тем же part_id,
    количеством и примечанием, procurement_status=not_ordered. Необязательные позиции
    (is_optional) копируются тоже: в OrderLine нет такого признака, решать, что из них
    не нужно, будет менеджер.

    Повторный apply ЗАМЕНЯЕТ результат предыдущего: старые строки с source=template
    удаляются и создаются заново по выбранному шаблону. Строки source=manual не
    трогаются. Так менеджер может исправить ошибочно выбранный шаблон, пока заказ в draft,
    а повторный apply того же шаблона не дублирует строки.

    Защита от потери данных: если по какой-то строке из шаблона закупка уже начата
    (procurement_status != not_ordered), заменять нельзя, будет 409.

    Заказ получает template_id и тип standard (по умолчанию заказ создаётся как custom).
    """
    order = await get_order_or_404(db, order_id)
    if order.status != OrderStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Применить шаблон можно только к заказу в статусе draft, сейчас: {order.status}"
            ),
        )

    template = await bom_service.get_template_or_404(db, template_id)
    if not template.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Шаблон BOM неактивен, применить его нельзя",
        )

    old_lines = (
        await db.scalars(
            select(OrderLine).where(
                OrderLine.order_id == order.id, OrderLine.source == OrderLineSource.template
            )
        )
    ).all()
    if any(line.procurement_status != ProcurementStatus.not_ordered for line in old_lines):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя заменить шаблон: по его строкам уже начаты закупки",
        )

    for line in old_lines:
        await db.delete(line)
    for item in template.items:
        db.add(
            OrderLine(
                order_id=order.id,
                part_id=item.part_id,
                quantity=item.quantity,
                source=OrderLineSource.template,
                note=item.note,
            )
        )
    order.template_id = template.id
    order.order_type = OrderType.standard
    await db.flush()

    return await get_order_with_lines(db, order.id)


async def get_order_with_lines(db: AsyncSession, order_id: UUID) -> Order:
    """Заказ вместе со строками.

    Строки подгружаем явно: в async-сессии обращение к `order.lines` без загрузки падает
    с MissingGreenlet. Заказ уже лежит в сессии без строк, а `populate_existing` заставляет
    SQLAlchemy заново заполнить этот объект данными из базы, включая строки.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.lines))
        .where(Order.id == order_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()
