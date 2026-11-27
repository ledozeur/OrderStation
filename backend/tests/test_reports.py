import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.order import Order, OrderLine, OrderStatus, ProcurementStatus

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


SUMMARY_URL = "/api/v1/reports/orders/{order_id}/procurement-summary"


async def create_part(client: AsyncClient, headers: dict[str, str]) -> uuid.UUID:
    response = await client.post(
        "/api/v1/parts", headers=headers, json={"sku": "SUM-1", "name": "Деталь"}
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def add_lines(
    session_factory: async_sessionmaker[AsyncSession],
    order_id: str,
    part_id: uuid.UUID,
    statuses: list[ProcurementStatus],
) -> None:
    """Кладёт в заказ по одной строке на каждый статус из списка (прямо в базу)."""
    async with session_factory() as session:
        session.add_all(
            OrderLine(order_id=uuid.UUID(order_id), part_id=part_id, procurement_status=s)
            for s in statuses
        )
        await session.commit()


async def summary(client: AsyncClient, headers: dict[str, str], order_id: str):
    return await client.get(SUMMARY_URL.format(order_id=order_id), headers=headers)


@pytest.mark.asyncio
async def test_summary_counts_by_status_and_percent_received(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    order = await create_order(client, auth_headers, customer_id, None, "заказ")
    part_id = await create_part(client, auth_headers)
    P = ProcurementStatus
    await add_lines(
        session_factory,
        order["id"],
        part_id,
        [P.not_ordered] * 2 + [P.ordered] * 5 + [P.received] * 3,
    )

    response = await summary(client, auth_headers, order["id"])

    assert response.status_code == 200, response.text
    assert response.json() == {
        "order_id": order["id"],
        "total_lines": 10,
        "by_status": {
            "not_ordered": 2,
            "ordered": 5,
            "in_transit": 0,
            "received": 3,
            "cancelled": 0,
        },
        "percent_received": 30.0,
    }


@pytest.mark.asyncio
async def test_summary_order_without_lines(
    client: AsyncClient, auth_headers: dict[str, str], customer_id: str
) -> None:
    order = await create_order(client, auth_headers, customer_id, None, "пустой")

    response = await summary(client, auth_headers, order["id"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_lines"] == 0
    assert body["percent_received"] == 0.0
    assert set(body["by_status"]) == {s.value for s in ProcurementStatus}
    assert all(count == 0 for count in body["by_status"].values())


@pytest.mark.asyncio
async def test_summary_cancelled_lines_stay_in_denominator(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    order = await create_order(client, auth_headers, customer_id, None, "заказ")
    part_id = await create_part(client, auth_headers)
    P = ProcurementStatus
    await add_lines(session_factory, order["id"], part_id, [P.received, P.cancelled])

    body = (await summary(client, auth_headers, order["id"])).json()

    assert body["total_lines"] == 2
    assert body["by_status"]["cancelled"] == 1
    assert body["percent_received"] == 50.0


@pytest.mark.asyncio
async def test_summary_percent_is_rounded_to_one_decimal(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    order = await create_order(client, auth_headers, customer_id, None, "заказ")
    part_id = await create_part(client, auth_headers)
    P = ProcurementStatus
    await add_lines(session_factory, order["id"], part_id, [P.received, P.ordered, P.ordered])

    body = (await summary(client, auth_headers, order["id"])).json()

    assert body["percent_received"] == 33.3


@pytest.mark.asyncio
async def test_summary_ignores_lines_of_other_orders(
    client: AsyncClient,
    auth_headers: dict[str, str],
    customer_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    target = await create_order(client, auth_headers, customer_id, None, "целевой")
    other = await create_order(client, auth_headers, customer_id, None, "чужой")
    part_id = await create_part(client, auth_headers)
    P = ProcurementStatus
    await add_lines(session_factory, target["id"], part_id, [P.ordered])
    await add_lines(session_factory, other["id"], part_id, [P.received] * 4)

    body = (await summary(client, auth_headers, target["id"])).json()

    assert body["total_lines"] == 1
    assert body["by_status"]["received"] == 0


@pytest.mark.asyncio
async def test_summary_unknown_order_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await summary(client, auth_headers, str(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["detail"] == "Заказ не найден"


@pytest.mark.asyncio
async def test_summary_invalid_order_id_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await summary(client, auth_headers, "не-uuid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summary_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(SUMMARY_URL.format(order_id=uuid.uuid4()))
    assert response.status_code == 401
