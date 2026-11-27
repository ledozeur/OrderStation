import uuid
from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.customer import Customer
from app.models.order import Order, OrderLine, ProcurementStatus
from app.models.part import Part
from app.models.user import User, UserRole
from app.services.procurement_service import (
    ALLOWED_PROCUREMENT_TRANSITIONS,
    update_line_procurement,
    validate_procurement_transition,
)
from app.utils.security import create_access_token, hash_password


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
    assert exc_info.value.status_code == 409


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

        line = await update_line_procurement(
            db_session,
            order.id,
            line.id,
            procurement_status=ProcurementStatus.in_transit,
            fields_set={"procurement_status"},
        )
        assert line.procurement_status == ProcurementStatus.in_transit

        line = await update_line_procurement(
            db_session,
            order.id,
            line.id,
            procurement_status=ProcurementStatus.received,
            fields_set={"procurement_status"},
        )
        assert line.procurement_status == ProcurementStatus.received
        assert line.actual_delivery_date is not None

        with pytest.raises(HTTPException) as exc_info:
            await update_line_procurement(
                db_session,
                order.id,
                line.id,
                procurement_status=ProcurementStatus.cancelled,
                fields_set={"procurement_status"},
            )
        assert exc_info.value.status_code == 409


async def _seed_order_line(session_factory: async_sessionmaker[AsyncSession], suffix: str):
    async with session_factory() as db:
        customer = Customer(name=f"Заказчик {suffix}")
        part = Part(sku=f"SKU-{suffix}", name=f"Деталь {suffix}")
        db.add_all([customer, part])
        await db.flush()

        order = Order(number=f"ORD-2026-{suffix}", customer_id=customer.id)
        db.add(order)
        await db.flush()

        line = OrderLine(order_id=order.id, part_id=part.id, quantity=3)
        db.add(line)
        await db.commit()
        return order.id, line.id


async def test_get_order_lines_includes_part_sku_and_name(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
):
    order_id, _line_id = await _seed_order_line(session_factory, "LINES-01")

    resp = await client.get(f"/api/v1/orders/{order_id}/lines", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["part_sku"] == "SKU-LINES-01"
    assert data[0]["part_name"] == "Деталь LINES-01"
    assert float(data[0]["quantity"]) == 3.0


@pytest.mark.asyncio
async def test_get_order_lines_not_found_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    resp = await client.get(f"/api/v1/orders/{uuid.uuid4()}/lines", headers=auth_headers)
    assert resp.status_code == 404


async def _make_user_headers(
    session_factory: async_sessionmaker[AsyncSession], email: str, role: UserRole
) -> dict[str, str]:
    async with session_factory() as db:
        user = User(
            email=email,
            hashed_password=hash_password("pass1234"),
            full_name=f"User {role.value}",
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
    token = create_access_token(email)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_patch_procurement_endpoint_happy_path_and_409(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
):
    order_id, line_id = await _seed_order_line(session_factory, "00101")
    proc_headers = await _make_user_headers(
        session_factory, "proc_tester@example.com", UserRole.procurement
    )

    # Попытка перепрыгнуть not_ordered -> received -> 409
    bad_resp = await client.patch(
        f"/api/v1/orders/{order_id}/lines/{line_id}/procurement",
        json={"procurement_status": "received"},
        headers=proc_headers,
    )
    assert bad_resp.status_code == 409

    # Нормальный переход not_ordered -> ordered
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    ok_resp = await client.patch(
        f"/api/v1/orders/{order_id}/lines/{line_id}/procurement",
        json={
            "procurement_status": "ordered",
            "supplier_name": "ООО ДронСнаб",
            "expected_delivery_date": tomorrow,
            "note": "Срочная поставка",
        },
        headers=proc_headers,
    )
    assert ok_resp.status_code == 200
    body = ok_resp.json()
    assert body["procurement_status"] == "ordered"
    assert body["supplier_name"] == "ООО ДронСнаб"
    assert body["ordered_at"] is not None


@pytest.mark.asyncio
async def test_patch_procurement_date_validation_422(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
):
    order_id, line_id = await _seed_order_line(session_factory, "00102")
    proc_headers = await _make_user_headers(
        session_factory, "proc_dates@example.com", UserRole.procurement
    )

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/lines/{line_id}/procurement",
        json={"procurement_status": "ordered", "expected_delivery_date": yesterday},
        headers=proc_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_procurement_rbac_viewer_403(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
):
    order_id, line_id = await _seed_order_line(session_factory, "00103")
    viewer_headers = await _make_user_headers(
        session_factory, "viewer_test@example.com", UserRole.viewer
    )

    resp = await client.patch(
        f"/api/v1/orders/{order_id}/lines/{line_id}/procurement",
        json={"procurement_status": "ordered"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_procurement_404_and_401(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    unauth = await client.patch(
        f"/api/v1/orders/{uuid.uuid4()}/lines/{uuid.uuid4()}/procurement",
        json={"procurement_status": "ordered"},
    )
    assert unauth.status_code == 401

    not_found = await client.patch(
        f"/api/v1/orders/{uuid.uuid4()}/lines/{uuid.uuid4()}/procurement",
        json={"procurement_status": "ordered"},
        headers=auth_headers,
    )
    assert not_found.status_code == 404


@pytest.mark.asyncio
async def test_bulk_patch_procurement_happy_path_and_atomic_rollback(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
):
    async with session_factory() as db:
        customer = Customer(name="ООО Массовая Закупка")
        p1 = Part(sku="BULK-PART-1", name="Мотор 1")
        p2 = Part(sku="BULK-PART-2", name="Мотор 2")
        db.add_all([customer, p1, p2])
        await db.flush()

        order = Order(number="ORD-2026-BULK1", customer_id=customer.id)
        db.add(order)
        await db.flush()

        l1 = OrderLine(order_id=order.id, part_id=p1.id, quantity=2)
        l2 = OrderLine(order_id=order.id, part_id=p2.id, quantity=4)
        db.add_all([l1, l2])
        await db.commit()
        order_id, l1_id, l2_id = order.id, l1.id, l2.id

    # 1. Успешное массовое обновление двух позиций (not_ordered -> ordered)
    ok_resp = await client.patch(
        f"/api/v1/orders/{order_id}/lines/procurement-bulk",
        json=[
            {"line_id": str(l1_id), "procurement_status": "ordered", "supplier_name": "Поставщик"},
            {"line_id": str(l2_id), "procurement_status": "ordered", "note": "Срочно"},
        ],
        headers=auth_headers,
    )
    assert ok_resp.status_code == 200
    body = ok_resp.json()
    assert len(body) == 2
    assert all(item["procurement_status"] == "ordered" for item in body)
    assert all(item["ordered_at"] is not None for item in body)

    # 2. Атомарный откат: первая позиция валидна (ordered -> in_transit),
    # вторая невалидна (ordered -> received запрещён -> 409) — ни одна не должна измениться
    bad_resp = await client.patch(
        f"/api/v1/orders/{order_id}/lines/procurement-bulk",
        json=[
            {"line_id": str(l1_id), "procurement_status": "in_transit"},
            {"line_id": str(l2_id), "procurement_status": "received"},
        ],
        headers=auth_headers,
    )
    assert bad_resp.status_code == 409

    check_resp = await client.get(f"/api/v1/orders/{order_id}/lines", headers=auth_headers)
    assert all(item["procurement_status"] == "ordered" for item in check_resp.json())


@pytest.mark.asyncio
async def test_bulk_patch_procurement_max_50_limit_422(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    oversized_payload = [
        {"line_id": str(uuid.uuid4()), "procurement_status": "ordered"} for _ in range(51)
    ]
    resp = await client.patch(
        f"/api/v1/orders/{uuid.uuid4()}/lines/procurement-bulk",
        json=oversized_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 422
