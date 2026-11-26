import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.order import Order, OrderStatus

URL = "/api/v1/reports/deadlines"
TODAY = date.today()


def days(offset: int) -> str:
    """Дата относительно сегодня в формате ГГГГ-ММ-ДД: days(-1) — вчера."""
    return (TODAY + timedelta(days=offset)).isoformat()


@pytest_asyncio.fixture
async def customer_id(client: AsyncClient, auth_headers: dict[str, str]) -> str:
    response = await client.post(
        "/api/v1/customers", headers=auth_headers, json={"name": "АвиаТех"}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def create_order(
    client: AsyncClient,
    headers: dict[str, str],
    customer_id: str,
    deadline: str | None,
    description: str,
) -> dict:
    """Создаёт заказ; description служит меткой, по которой заказы узнаются в ответе."""
    body: dict[str, str | None] = {"customer_id": customer_id, "description": description}
    if deadline is not None:
        body["deadline_date"] = deadline
    response = await client.post("/api/v1/orders", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def set_status(
    session_factory: async_sessionmaker[AsyncSession], order_id: str, new_status: OrderStatus
) -> None:
    async with session_factory() as session:
        order = await session.get(Order, uuid.UUID(order_id))
        assert order is not None
        order.status = new_status
        await session.commit()


async def report(client: AsyncClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Возвращает описания заказов из отчёта в порядке ответа."""
    response = await client.get(f"{URL}{query}", headers=headers)
    assert response.status_code == 200, response.text
    return [row["description"] for row in response.json()]


@pytest.mark.asyncio
async def test_overdue_returns_only_past_deadlines(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    await create_order(client, auth_headers, customer_id, days(-10), "давно")
    await create_order(client, auth_headers, customer_id, days(-1), "вчера")
    await create_order(client, auth_headers, customer_id, days(0), "сегодня")
    await create_order(client, auth_headers, customer_id, days(5), "скоро")
    await create_order(client, auth_headers, customer_id, None, "без срока")

    # Сегодняшний срок ещё не просрочен; самые старые сроки идут первыми.
    assert await report(client, auth_headers, "?overdue=true") == ["давно", "вчера"]


@pytest.mark.asyncio
async def test_overdue_excludes_completed_and_cancelled(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    open_order = await create_order(client, auth_headers, customer_id, days(-3), "открыт")
    completed = await create_order(client, auth_headers, customer_id, days(-3), "завершён")
    cancelled = await create_order(client, auth_headers, customer_id, days(-3), "отменён")
    in_procurement = await create_order(client, auth_headers, customer_id, days(-3), "в закупке")
    await set_status(session_factory, completed["id"], OrderStatus.completed)
    await set_status(session_factory, cancelled["id"], OrderStatus.cancelled)
    await set_status(session_factory, in_procurement["id"], OrderStatus.in_procurement)

    result = await report(client, auth_headers, "?overdue=true")

    assert sorted(result) == ["в закупке", "открыт"]
    assert open_order["description"] in result


@pytest.mark.asyncio
async def test_due_in_days_window_includes_both_boundaries(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    await create_order(client, auth_headers, customer_id, days(-1), "вчера")
    await create_order(client, auth_headers, customer_id, days(0), "сегодня")
    await create_order(client, auth_headers, customer_id, days(3), "через 3")
    await create_order(client, auth_headers, customer_id, days(7), "через 7")
    await create_order(client, auth_headers, customer_id, days(8), "через 8")

    assert await report(client, auth_headers, "?due_in_days=7") == [
        "сегодня",
        "через 3",
        "через 7",
    ]
    # N = 0 — только заказы со сроком сегодня.
    assert await report(client, auth_headers, "?due_in_days=0") == ["сегодня"]


@pytest.mark.asyncio
async def test_due_in_days_excludes_closed_orders(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await create_order(client, auth_headers, customer_id, days(2), "открыт")
    done = await create_order(client, auth_headers, customer_id, days(2), "завершён")
    await set_status(session_factory, done["id"], OrderStatus.completed)

    assert await report(client, auth_headers, "?due_in_days=5") == ["открыт"]


@pytest.mark.asyncio
async def test_overdue_and_due_in_days_are_combined_with_or(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    await create_order(client, auth_headers, customer_id, days(-2), "просрочен")
    await create_order(client, auth_headers, customer_id, days(4), "скоро")
    await create_order(client, auth_headers, customer_id, days(30), "далеко")

    assert await report(client, auth_headers, "?overdue=true&due_in_days=7") == [
        "просрочен",
        "скоро",
    ]


@pytest.mark.asyncio
async def test_without_params_returns_all_open_orders_with_deadline(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    await create_order(client, auth_headers, customer_id, days(10), "позже")
    await create_order(client, auth_headers, customer_id, days(-5), "раньше")
    await create_order(client, auth_headers, customer_id, None, "без срока")

    assert await report(client, auth_headers) == ["раньше", "позже"]


@pytest.mark.asyncio
async def test_report_empty_result(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    await create_order(client, auth_headers, customer_id, days(30), "далеко")

    assert await report(client, auth_headers, "?overdue=true") == []
    assert await report(client, auth_headers, "?due_in_days=7") == []


@pytest.mark.asyncio
async def test_report_empty_database(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    assert await report(client, auth_headers) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["?due_in_days=-1", "?due_in_days=abc", "?overdue=maybe"])
async def test_report_invalid_params_return_422(
    client: AsyncClient, auth_headers: dict[str, str], query: str
) -> None:
    response = await client.get(f"{URL}{query}", headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_report_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(URL)
    assert response.status_code == 401
