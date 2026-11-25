import re
import uuid
from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.services import order_service
from app.utils.order_number import format_order_number
from app.utils.security import hash_password

URL = "/api/v1/orders"
YEAR = date.today().year


def number(sequence: int) -> str:
    """Номер заказа за текущий год: number(3) -> ORD-<год>-00003."""
    return format_order_number(YEAR, sequence)


async def create_customer(client: AsyncClient, headers: dict[str, str], name: str) -> str:
    response = await client.post("/api/v1/customers", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def create_order(
    client: AsyncClient, headers: dict[str, str], customer_id: str, **extra: str
) -> dict:
    """Создаёт заказ и возвращает JSON ответа (проверяя, что вернулся 201)."""
    response = await client.post(URL, headers=headers, json={"customer_id": customer_id, **extra})
    assert response.status_code == 201, response.text
    return response.json()


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
async def customer_id(client: AsyncClient, auth_headers: dict[str, str]) -> str:
    return await create_customer(client, auth_headers, "АвиаТех")


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


# --- Создание ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_order_returns_draft_with_number(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    order = await create_order(client, auth_headers, customer_id)

    assert order["number"] == number(1)
    assert order["status"] == "draft"
    assert order["order_type"] == "custom"
    assert order["customer_id"] == customer_id
    assert order["template_id"] is None
    assert order["deadline_date"] is None
    assert order["description"] is None
    assert order["confirmed_at"] is None
    assert order["id"]
    assert order["created_at"]


@pytest.mark.asyncio
async def test_create_order_with_deadline_and_description(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    order = await create_order(
        client,
        auth_headers,
        customer_id,
        deadline_date="2026-12-31",
        description="Партия из 10 дронов",
    )

    assert order["deadline_date"] == "2026-12-31"
    assert order["description"] == "Партия из 10 дронов"
    fetched = await client.get(f"{URL}/{order['id']}", headers=auth_headers)
    assert fetched.json()["deadline_date"] == "2026-12-31"


@pytest.mark.asyncio
async def test_create_orders_get_sequential_unique_numbers(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    numbers = [(await create_order(client, auth_headers, customer_id))["number"] for _ in range(3)]

    assert numbers == [number(1), number(2), number(3)]
    assert re.fullmatch(rf"ORD-{YEAR}-\d{{5}}", numbers[0])


@pytest.mark.asyncio
async def test_create_order_unknown_customer_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(URL, headers=auth_headers, json={"customer_id": str(uuid.uuid4())})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_order_without_customer_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(URL, headers=auth_headers, json={"description": "Без заказчика"})
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "extra",
    [{"customer_id": "не-uuid"}, {"deadline_date": "31.12.2026"}, {"deadline_date": "завтра"}],
)
async def test_create_order_invalid_values_return_422(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str, extra: dict[str, str]
) -> None:
    response = await client.post(
        URL, headers=auth_headers, json={"customer_id": customer_id, **extra}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_order_retries_when_number_is_taken(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Если параллельный запрос занял номер, создание повторяется с новым номером."""
    first = await create_order(client, auth_headers, customer_id)
    proposed = iter([first["number"], number(2)])

    async def fake_generate(db: AsyncSession) -> str:
        return next(proposed)

    monkeypatch.setattr(order_service, "generate_order_number", fake_generate)

    second = await create_order(client, auth_headers, customer_id)

    assert second["number"] == number(2)


@pytest.mark.asyncio
async def test_create_order_returns_409_when_number_cannot_be_issued(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = await create_order(client, auth_headers, customer_id)

    async def always_taken(db: AsyncSession) -> str:
        return first["number"]

    monkeypatch.setattr(order_service, "generate_order_number", always_taken)

    response = await client.post(URL, headers=auth_headers, json={"customer_id": customer_id})

    assert response.status_code == 409
    listed = await client.get(URL, headers=auth_headers)
    assert len(listed.json()) == 1


# --- Чтение -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_order_by_id(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    created = await create_order(client, auth_headers, customer_id)

    response = await client.get(f"{URL}/{created['id']}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.asyncio
async def test_get_order_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get(f"{URL}/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_order_invalid_id_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(f"{URL}/не-uuid", headers=auth_headers)
    assert response.status_code == 422


# --- Реестр: список, фильтры, пагинация ---------------------------------------------------


@pytest.mark.asyncio
async def test_list_orders_returns_newest_first(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    for _ in range(3):
        await create_order(client, auth_headers, customer_id)

    response = await client.get(URL, headers=auth_headers)

    assert response.status_code == 200
    assert [row["number"] for row in response.json()] == [number(3), number(2), number(1)]


@pytest.mark.asyncio
async def test_list_orders_empty(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get(URL, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_orders_filter_by_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    draft = await create_order(client, auth_headers, customer_id)
    confirmed = await create_order(client, auth_headers, customer_id)
    cancelled = await create_order(client, auth_headers, customer_id)
    await set_status(session_factory, confirmed["id"], OrderStatus.confirmed)
    await set_status(session_factory, cancelled["id"], OrderStatus.cancelled)

    async def numbers_with(order_status: str) -> list[str]:
        response = await client.get(f"{URL}?status={order_status}", headers=auth_headers)
        assert response.status_code == 200, response.text
        return [row["number"] for row in response.json()]

    assert await numbers_with("draft") == [draft["number"]]
    assert await numbers_with("confirmed") == [confirmed["number"]]
    assert await numbers_with("cancelled") == [cancelled["number"]]
    assert await numbers_with("completed") == []


@pytest.mark.asyncio
async def test_list_orders_filter_by_customer(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    other_customer_id = await create_customer(client, auth_headers, "Беспилотные системы")
    first = await create_order(client, auth_headers, customer_id)
    second = await create_order(client, auth_headers, other_customer_id)
    third = await create_order(client, auth_headers, customer_id)

    async def numbers_of(customer: str) -> list[str]:
        response = await client.get(f"{URL}?customer_id={customer}", headers=auth_headers)
        assert response.status_code == 200, response.text
        return [row["number"] for row in response.json()]

    assert await numbers_of(customer_id) == [third["number"], first["number"]]
    assert await numbers_of(other_customer_id) == [second["number"]]
    assert await numbers_of(str(uuid.uuid4())) == []


@pytest.mark.asyncio
async def test_list_orders_pagination(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    for _ in range(5):
        await create_order(client, auth_headers, customer_id)

    async def numbers_on(query: str) -> list[str]:
        response = await client.get(f"{URL}{query}", headers=auth_headers)
        assert response.status_code == 200, response.text
        return [row["number"] for row in response.json()]

    assert await numbers_on("?limit=2") == [number(5), number(4)]
    assert await numbers_on("?limit=2&offset=2") == [number(3), number(2)]
    assert await numbers_on("?limit=2&offset=4") == [number(1)]
    assert await numbers_on("?limit=2&offset=10") == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    ["?limit=0", "?limit=101", "?offset=-1", "?status=unknown", "?customer_id=не-uuid"],
)
async def test_list_orders_invalid_params_return_422(
    client: AsyncClient, auth_headers: dict[str, str], query: str
) -> None:
    response = await client.get(f"{URL}{query}", headers=auth_headers)
    assert response.status_code == 422


# --- Изменение (только draft) -----------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_draft_order(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    order = await create_order(client, auth_headers, customer_id, description="Черновик")

    response = await client.patch(
        f"{URL}/{order['id']}",
        headers=auth_headers,
        json={"description": "Партия из 10 дронов", "deadline_date": "2026-12-31"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Партия из 10 дронов"
    assert body["deadline_date"] == "2026-12-31"
    # Номер, статус и заказчик, которых не было в запросе, не меняются.
    assert body["number"] == order["number"]
    assert body["status"] == "draft"
    assert body["customer_id"] == customer_id


@pytest.mark.asyncio
async def test_patch_draft_order_changes_customer(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    other_customer_id = await create_customer(client, auth_headers, "Беспилотные системы")
    order = await create_order(client, auth_headers, customer_id)

    response = await client.patch(
        f"{URL}/{order['id']}", headers=auth_headers, json={"customer_id": other_customer_id}
    )

    assert response.status_code == 200
    assert response.json()["customer_id"] == other_customer_id


@pytest.mark.asyncio
async def test_patch_draft_order_can_clear_deadline(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    order = await create_order(client, auth_headers, customer_id, deadline_date="2026-12-31")

    response = await client.patch(
        f"{URL}/{order['id']}", headers=auth_headers, json={"deadline_date": None}
    )

    assert response.status_code == 200
    assert response.json()["deadline_date"] is None


@pytest.mark.asyncio
async def test_patch_order_unknown_customer_returns_404(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    order = await create_order(client, auth_headers, customer_id)

    response = await client.patch(
        f"{URL}/{order['id']}", headers=auth_headers, json={"customer_id": str(uuid.uuid4())}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_order_null_customer_returns_422(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    order = await create_order(client, auth_headers, customer_id)

    response = await client.patch(
        f"{URL}/{order['id']}", headers=auth_headers, json={"customer_id": None}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_order_invalid_deadline_returns_422(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    order = await create_order(client, auth_headers, customer_id)

    response = await client.patch(
        f"{URL}/{order['id']}", headers=auth_headers, json={"deadline_date": "завтра"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_order_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.patch(
        f"{URL}/{uuid.uuid4()}", headers=auth_headers, json={"description": "X"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "locked_status",
    [
        OrderStatus.confirmed,
        OrderStatus.in_procurement,
        OrderStatus.completed,
        OrderStatus.cancelled,
    ],
)
async def test_patch_order_not_in_draft_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    locked_status: OrderStatus,
) -> None:
    order = await create_order(client, auth_headers, customer_id, description="Исходное")
    await set_status(session_factory, order["id"], locked_status)

    response = await client.patch(
        f"{URL}/{order['id']}", headers=auth_headers, json={"description": "Новое"}
    )

    assert response.status_code == 409
    unchanged = await client.get(f"{URL}/{order['id']}", headers=auth_headers)
    assert unchanged.json()["description"] == "Исходное"


# --- Права доступа ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orders_require_authentication(client: AsyncClient) -> None:
    response = await client.get(URL)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_viewer_can_read_orders(
    client: AsyncClient,
    auth_headers: dict[str, str],
    viewer_headers: dict[str, str],
    customer_id: str,
) -> None:
    order = await create_order(client, auth_headers, customer_id)

    listed = await client.get(URL, headers=viewer_headers)
    fetched = await client.get(f"{URL}/{order['id']}", headers=viewer_headers)

    assert listed.status_code == 200
    assert fetched.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_create_order(
    client: AsyncClient, viewer_headers: dict[str, str], customer_id: str
) -> None:
    response = await client.post(URL, headers=viewer_headers, json={"customer_id": customer_id})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_update_order(
    client: AsyncClient,
    auth_headers: dict[str, str],
    viewer_headers: dict[str, str],
    customer_id: str,
) -> None:
    order = await create_order(client, auth_headers, customer_id)

    response = await client.patch(
        f"{URL}/{order['id']}", headers=viewer_headers, json={"description": "Чужое"}
    )

    assert response.status_code == 403
