import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.order import (
    Order,
    OrderLine,
    OrderLineSource,
    OrderStatus,
    ProcurementStatus,
)
from app.models.user import User, UserRole
from app.utils.security import hash_password

ORDERS = "/api/v1/orders"


# --- Помощники --------------------------------------------------------------------------


async def create_order(client: AsyncClient, headers: dict[str, str]) -> str:
    """Создаёт заказчика и пустой заказ в статусе draft, возвращает id заказа."""
    customer = await client.post("/api/v1/customers", headers=headers, json={"name": "АвиаТех"})
    assert customer.status_code == 201, customer.text
    order = await client.post(ORDERS, headers=headers, json={"customer_id": customer.json()["id"]})
    assert order.status_code == 201, order.text
    return order.json()["id"]


async def create_part(client: AsyncClient, headers: dict[str, str], sku: str) -> str:
    response = await client.post(
        "/api/v1/parts", headers=headers, json={"sku": sku, "name": f"Деталь {sku}"}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def create_template(
    client: AsyncClient,
    headers: dict[str, str],
    code: str,
    items: list[dict],
    *,
    is_active: bool = True,
) -> str:
    """Создаёт шаблон BOM с позициями `items` (part_id, quantity, note) и возвращает его id."""
    response = await client.post(
        "/api/v1/bom-templates",
        headers=headers,
        json={"code": code, "name": f"Шаблон {code}", "is_active": is_active},
    )
    assert response.status_code == 201, response.text
    template_id = response.json()["id"]
    for item in items:
        added = await client.post(
            f"/api/v1/bom-templates/{template_id}/items", headers=headers, json=item
        )
        assert added.status_code == 201, added.text
    return template_id


async def apply_template(
    client: AsyncClient, headers: dict[str, str], order_id: str, template_id: str
) -> Response:
    return await client.post(
        f"{ORDERS}/{order_id}/apply-template", headers=headers, json={"template_id": template_id}
    )


async def lines_in_db(
    session_factory: async_sessionmaker[AsyncSession], order_id: str
) -> list[OrderLine]:
    """Строки заказа, прочитанные прямо из базы (а не из ответа API)."""
    async with session_factory() as session:
        result = await session.scalars(
            select(OrderLine).where(OrderLine.order_id == uuid.UUID(order_id))
        )
        return list(result.all())


async def set_status(
    session_factory: async_sessionmaker[AsyncSession], order_id: str, new_status: OrderStatus
) -> None:
    """Меняет статус заказа напрямую в базе: confirm/cancel через API появятся позже."""
    async with session_factory() as session:
        order = await session.get(Order, uuid.UUID(order_id))
        assert order is not None
        order.status = new_status
        await session.commit()


@pytest_asyncio.fixture
async def viewer_headers(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> dict[str, str]:
    """Заголовки авторизации пользователя с ролью viewer (только чтение)."""
    async with session_factory() as session:
        session.add(
            User(
                email="viewer@example.com",
                hashed_password=hash_password("viewer"),
                full_name="Demo Viewer",
                role=UserRole.viewer,
            )
        )
        await session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "viewer@example.com", "password": "viewer"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- Основной сценарий ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_template_copies_bom_items_to_order_lines(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """E2E: BOM -> заказ -> apply -> строки в ответе и в базе."""
    frame = await create_part(client, auth_headers, "FRAME-1")
    motor = await create_part(client, auth_headers, "MOTOR-1")
    battery = await create_part(client, auth_headers, "BAT-1")
    template_id = await create_template(
        client,
        auth_headers,
        "UAV-1",
        [
            {"part_id": frame, "quantity": 1},
            {"part_id": motor, "quantity": 4, "note": "по часовой и против"},
            {"part_id": battery, "quantity": 1.5, "is_optional": True},
        ],
    )
    order_id = await create_order(client, auth_headers)

    response = await apply_template(client, auth_headers, order_id, template_id)

    assert response.status_code == 200, response.text
    order = response.json()
    assert order["id"] == order_id
    assert order["status"] == "draft"
    assert order["template_id"] == template_id
    assert order["order_type"] == "standard"

    assert len(order["lines"]) == 3
    by_part = {line["part_id"]: line for line in order["lines"]}
    assert set(by_part) == {frame, motor, battery}
    assert Decimal(str(by_part[frame]["quantity"])) == Decimal("1")
    assert Decimal(str(by_part[motor]["quantity"])) == Decimal("4")
    assert Decimal(str(by_part[battery]["quantity"])) == Decimal("1.5")
    assert by_part[motor]["note"] == "по часовой и против"
    assert by_part[frame]["note"] is None
    for line in order["lines"]:
        assert line["order_id"] == order_id
        assert line["source"] == "template"
        assert line["procurement_status"] == "not_ordered"

    # Строки действительно сохранены, а не только показаны в ответе.
    saved = await lines_in_db(session_factory, order_id)
    assert len(saved) == 3
    assert {line.part_id for line in saved} == {uuid.UUID(p) for p in (frame, motor, battery)}

    # Шаблон и тип заказа тоже сохранились.
    fetched = await client.get(f"{ORDERS}/{order_id}", headers=auth_headers)
    assert fetched.json()["template_id"] == template_id
    assert fetched.json()["order_type"] == "standard"


@pytest.mark.asyncio
async def test_apply_empty_template_sets_template_and_creates_no_lines(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    template_id = await create_template(client, auth_headers, "EMPTY", [])
    order_id = await create_order(client, auth_headers)

    response = await apply_template(client, auth_headers, order_id, template_id)

    assert response.status_code == 200, response.text
    assert response.json()["lines"] == []
    assert response.json()["template_id"] == template_id


# --- Повторный apply --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_same_template_twice_does_not_duplicate_lines(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    frame = await create_part(client, auth_headers, "FRAME-1")
    motor = await create_part(client, auth_headers, "MOTOR-1")
    template_id = await create_template(
        client,
        auth_headers,
        "UAV-1",
        [{"part_id": frame, "quantity": 1}, {"part_id": motor, "quantity": 4}],
    )
    order_id = await create_order(client, auth_headers)

    first = await apply_template(client, auth_headers, order_id, template_id)
    second = await apply_template(client, auth_headers, order_id, template_id)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert len(second.json()["lines"]) == 2
    assert len(await lines_in_db(session_factory, order_id)) == 2


@pytest.mark.asyncio
async def test_apply_another_template_replaces_template_lines_and_keeps_manual(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    frame = await create_part(client, auth_headers, "FRAME-1")
    motor = await create_part(client, auth_headers, "MOTOR-1")
    cable = await create_part(client, auth_headers, "CABLE-1")
    first_template = await create_template(
        client,
        auth_headers,
        "UAV-1",
        [{"part_id": frame, "quantity": 1}, {"part_id": motor, "quantity": 4}],
    )
    second_template = await create_template(
        client, auth_headers, "UAV-2", [{"part_id": cable, "quantity": 10}]
    )
    order_id = await create_order(client, auth_headers)
    await apply_template(client, auth_headers, order_id, first_template)

    # Строку вручную через API пока не добавить: кладём её прямо в базу.
    async with session_factory() as session:
        session.add(
            OrderLine(
                order_id=uuid.UUID(order_id),
                part_id=uuid.UUID(frame),
                quantity=2,
                source=OrderLineSource.manual,
            )
        )
        await session.commit()

    response = await apply_template(client, auth_headers, order_id, second_template)

    assert response.status_code == 200, response.text
    order = response.json()
    assert order["template_id"] == second_template
    sources = sorted((line["source"], line["part_id"]) for line in order["lines"])
    assert sources == sorted([("manual", frame), ("template", cable)])
    assert len(await lines_in_db(session_factory, order_id)) == 2


@pytest.mark.asyncio
async def test_reapply_after_procurement_started_returns_409_and_keeps_lines(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    frame = await create_part(client, auth_headers, "FRAME-1")
    motor = await create_part(client, auth_headers, "MOTOR-1")
    template_id = await create_template(
        client,
        auth_headers,
        "UAV-1",
        [{"part_id": frame, "quantity": 1}, {"part_id": motor, "quantity": 4}],
    )
    order_id = await create_order(client, auth_headers)
    await apply_template(client, auth_headers, order_id, template_id)

    saved = await lines_in_db(session_factory, order_id)
    async with session_factory() as session:
        line = await session.get(OrderLine, saved[0].id)
        assert line is not None
        line.procurement_status = ProcurementStatus.ordered
        await session.commit()

    response = await apply_template(client, auth_headers, order_id, template_id)

    assert response.status_code == 409
    after = await lines_in_db(session_factory, order_id)
    assert {line.id for line in after} == {line.id for line in saved}
    assert [line.procurement_status for line in after if line.id == saved[0].id] == [
        ProcurementStatus.ordered
    ]


# --- Ограничения: 409 -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_inactive_template_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    frame = await create_part(client, auth_headers, "FRAME-1")
    template_id = await create_template(
        client, auth_headers, "OLD", [{"part_id": frame, "quantity": 1}], is_active=False
    )
    order_id = await create_order(client, auth_headers)

    response = await apply_template(client, auth_headers, order_id, template_id)

    assert response.status_code == 409
    assert "неактивен" in response.json()["detail"]
    assert await lines_in_db(session_factory, order_id) == []
    order = await client.get(f"{ORDERS}/{order_id}", headers=auth_headers)
    assert order.json()["template_id"] is None
    assert order.json()["order_type"] == "custom"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "order_status",
    [
        OrderStatus.confirmed,
        OrderStatus.in_procurement,
        OrderStatus.completed,
        OrderStatus.cancelled,
    ],
)
async def test_apply_template_to_non_draft_order_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
    order_status: OrderStatus,
) -> None:
    frame = await create_part(client, auth_headers, "FRAME-1")
    template_id = await create_template(
        client, auth_headers, "UAV-1", [{"part_id": frame, "quantity": 1}]
    )
    order_id = await create_order(client, auth_headers)
    await set_status(session_factory, order_id, order_status)

    response = await apply_template(client, auth_headers, order_id, template_id)

    assert response.status_code == 409
    assert "draft" in response.json()["detail"]
    assert await lines_in_db(session_factory, order_id) == []


# --- Ограничения: 404 / 403 / 401 / 422 -------------------------------------------------


@pytest.mark.asyncio
async def test_apply_template_unknown_order_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    template_id = await create_template(client, auth_headers, "UAV-1", [])

    response = await apply_template(client, auth_headers, str(uuid.uuid4()), template_id)

    assert response.status_code == 404
    assert response.json()["detail"] == "Заказ не найден"


@pytest.mark.asyncio
async def test_apply_unknown_template_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    order_id = await create_order(client, auth_headers)

    response = await apply_template(client, auth_headers, order_id, str(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["detail"] == "Шаблон BOM не найден"


@pytest.mark.asyncio
async def test_apply_template_requires_manager_role(
    client: AsyncClient, auth_headers: dict[str, str], viewer_headers: dict[str, str]
) -> None:
    template_id = await create_template(client, auth_headers, "UAV-1", [])
    order_id = await create_order(client, auth_headers)

    response = await apply_template(client, viewer_headers, order_id, template_id)

    assert response.status_code == 403
    order = await client.get(f"{ORDERS}/{order_id}", headers=auth_headers)
    assert order.json()["template_id"] is None


@pytest.mark.asyncio
async def test_apply_template_without_token_returns_401(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    template_id = await create_template(client, auth_headers, "UAV-1", [])
    order_id = await create_order(client, auth_headers)

    response = await client.post(
        f"{ORDERS}/{order_id}/apply-template", json={"template_id": template_id}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{}, {"template_id": None}, {"template_id": "не-uuid"}])
async def test_apply_template_invalid_body_returns_422(
    client: AsyncClient, auth_headers: dict[str, str], body: dict
) -> None:
    order_id = await create_order(client, auth_headers)

    response = await client.post(
        f"{ORDERS}/{order_id}/apply-template", headers=auth_headers, json=body
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_apply_template_invalid_order_id_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        f"{ORDERS}/не-uuid/apply-template",
        headers=auth_headers,
        json={"template_id": str(uuid.uuid4())},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_apply_template_does_not_change_other_orders(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    frame = await create_part(client, auth_headers, "FRAME-1")
    template_id = await create_template(
        client, auth_headers, "UAV-1", [{"part_id": frame, "quantity": 1}]
    )
    target = await create_order(client, auth_headers)
    other = await create_order(client, auth_headers)

    response = await apply_template(client, auth_headers, target, template_id)

    assert response.status_code == 200, response.text
    assert await lines_in_db(session_factory, other) == []
    async with session_factory() as session:
        total = await session.scalar(select(func.count()).select_from(OrderLine))
    assert total == 1
