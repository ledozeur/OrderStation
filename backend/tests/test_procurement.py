import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.customer import Customer
from app.models.order import Order, OrderLine, ProcurementStatus
from app.models.part import Part
from app.services.procurement_service import (
    ALLOWED_PROCUREMENT_TRANSITIONS,
    update_line_procurement,
    validate_procurement_transition,
)


@pytest.mark.parametrize(
    ("src", "dst"),
    [
        (ProcurementStatus.not_ordered, ProcurementStatus.ordered),
        (ProcurementStatus.not_ordered, ProcurementStatus.cancelled),
        (ProcurementStatus.ordered, ProcurementStatus.in_transit),
        (ProcurementStatus.ordered, ProcurementStatus.cancelled),
        (ProcurementStatus.in_transit, ProcurementStatus.received),
        (ProcurementStatus.in_transit, ProcurementStatus.cancelled),
        (ProcurementStatus.ordered, ProcurementStatus.ordered),
    ],
)
def test_valid_procurement_transitions(src: ProcurementStatus, dst: ProcurementStatus):
    validate_procurement_transition(src, dst)


@pytest.mark.parametrize(
    ("src", "dst"),
    [
        (ProcurementStatus.not_ordered, ProcurementStatus.in_transit),
        (ProcurementStatus.not_ordered, ProcurementStatus.received),
        (ProcurementStatus.ordered, ProcurementStatus.not_ordered),
        (ProcurementStatus.ordered, ProcurementStatus.received),
        (ProcurementStatus.in_transit, ProcurementStatus.ordered),
        (ProcurementStatus.in_transit, ProcurementStatus.not_ordered),
        (ProcurementStatus.received, ProcurementStatus.cancelled),
        (ProcurementStatus.received, ProcurementStatus.in_transit),
        (ProcurementStatus.cancelled, ProcurementStatus.not_ordered),
        (ProcurementStatus.cancelled, ProcurementStatus.ordered),
    ],
)
def test_invalid_procurement_transitions(src: ProcurementStatus, dst: ProcurementStatus):
    with pytest.raises(HTTPException) as exc_info:
        validate_procurement_transition(src, dst)
    assert exc_info.value.status_code == 422


def test_all_statuses_covered_in_matrix():
    assert set(ALLOWED_PROCUREMENT_TRANSITIONS.keys()) == set(ProcurementStatus)


@pytest.mark.asyncio
async def test_update_line_procurement_lifecycle(
    session_factory: async_sessionmaker[AsyncSession],
):
    async with session_factory() as db_session:
        customer = Customer(name="ООО Тест Закупки")
        part = Part(sku="PROC-PART-1", name="Контроллер полёта")
        db_session.add_all([customer, part])
        await db_session.flush()

        order = Order(number="ORD-PROC-001", customer_id=customer.id)
        db_session.add(order)
        await db_session.flush()

        line = OrderLine(order_id=order.id, part_id=part.id, quantity=2)
        db_session.add(line)
        await db_session.commit()
        await db_session.refresh(line)

        assert line.procurement_status == ProcurementStatus.not_ordered
        assert line.ordered_at is None

        # 1. Переход not_ordered -> ordered (проставляется ordered_at)
        line = await update_line_procurement(
            db_session,
            order.id,
            line.id,
            procurement_status=ProcurementStatus.ordered,
            supplier_name="Поставщик Альфа",
            fields_set={"procurement_status", "supplier_name"},
        )
        assert line.procurement_status == ProcurementStatus.ordered
        assert line.ordered_at is not None
        assert line.supplier_name == "Поставщик Альфа"

        # 2. Переход ordered -> in_transit
        line = await update_line_procurement(
            db_session,
            order.id,
            line.id,
            procurement_status=ProcurementStatus.in_transit,
            fields_set={"procurement_status"},
        )
        assert line.procurement_status == ProcurementStatus.in_transit

        # 3. Переход in_transit -> received (проставляется actual_delivery_date)
        line = await update_line_procurement(
            db_session,
            order.id,
            line.id,
            procurement_status=ProcurementStatus.received,
            fields_set={"procurement_status"},
        )
        assert line.procurement_status == ProcurementStatus.received
        assert line.actual_delivery_date is not None

        # 4. Попытка изменить терминальный статус received -> cancelled вызывает 422
        with pytest.raises(HTTPException) as exc_info:
            await update_line_procurement(
                db_session,
                order.id,
                line.id,
                procurement_status=ProcurementStatus.cancelled,
                fields_set={"procurement_status"},
            )
        assert exc_info.value.status_code == 422
