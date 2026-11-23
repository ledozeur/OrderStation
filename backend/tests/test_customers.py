import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User, UserRole
from app.utils.security import hash_password

URL = "/api/v1/customers"


async def create_customer(
    client: AsyncClient, headers: dict[str, str], name: str, **extra: str
) -> dict:
    """создаёт заказчика и возвращает JSON ответа (проверяя, что вернулся 201)"""
    response = await client.post(URL, headers=headers, json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


async def list_names(client: AsyncClient, headers: dict[str, str], query: str = "") -> list[str]:
    response = await client.get(f"{URL}{query}", headers=headers)
    assert response.status_code == 200, response.text
    return [row["name"] for row in response.json()]


@pytest_asyncio.fixture
async def viewer_headers(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> dict[str, str]:
    """заголовки авторизации пользователя с ролью viewer (read only)"""
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


# --- создание, чтение, обновление, удаление ---------------------------------------------


@pytest.mark.asyncio
async def test_create_and_list_customer(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    create = await client.post(
        URL,
        headers=auth_headers,
        json={"name": "АвиаТех", "contact_person": "Иванов"},
    )
    assert create.status_code == 201
    customer_id = create.json()["id"]

    listed = await client.get(URL, headers=auth_headers)
    assert listed.status_code == 200
    assert any(row["id"] == customer_id for row in listed.json())

    got = await client.get(f"{URL}/{customer_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["name"] == "АвиаТех"


@pytest.mark.asyncio
async def test_update_customer(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    customer = await create_customer(client, auth_headers, "АвиаТех", contact_person="Иванов")

    response = await client.patch(
        f"{URL}/{customer['id']}", headers=auth_headers, json={"name": "АвиаТех-2"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "АвиаТех-2"
    # поля, которых не было в запросе, не меняются
    assert body["contact_person"] == "Иванов"


@pytest.mark.asyncio
async def test_delete_customer(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    customer = await create_customer(client, auth_headers, "АвиаТех")

    deleted = await client.delete(f"{URL}/{customer['id']}", headers=auth_headers)
    assert deleted.status_code == 204

    got = await client.get(f"{URL}/{customer['id']}", headers=auth_headers)
    assert got.status_code == 404


# --- 404 ---------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_customer_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get(f"{URL}/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_customer_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.patch(f"{URL}/{uuid.uuid4()}", headers=auth_headers, json={"name": "X"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_customer_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.delete(f"{URL}/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


# --- Валидация (422) ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_customer_empty_name_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(URL, headers=auth_headers, json={"name": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_customer_blank_name_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(URL, headers=auth_headers, json={"name": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_customer_without_name_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(URL, headers=auth_headers, json={"contact_person": "Иванов"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_customer_invalid_email_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        URL, headers=auth_headers, json={"name": "АвиаТех", "email": "не-email"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_customer_empty_name_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    customer = await create_customer(client, auth_headers, "АвиаТех")

    response = await client.patch(
        f"{URL}/{customer['id']}", headers=auth_headers, json={"name": ""}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_customer_null_name_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """явный null в name — ошибка валидации, а не падение базы данных (500)"""
    customer = await create_customer(client, auth_headers, "АвиаТех")

    response = await client.patch(
        f"{URL}/{customer['id']}", headers=auth_headers, json={"name": None}
    )

    assert response.status_code == 422


# --- Поиск q -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_by_name_is_case_insensitive(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    for name in ("Aero Dynamics", "AeroTech", "Beta Works"):
        await create_customer(client, auth_headers, name)

    assert await list_names(client, auth_headers, "?q=aero") == ["Aero Dynamics", "AeroTech"]
    assert await list_names(client, auth_headers, "?q=WORKS") == ["Beta Works"]


@pytest.mark.asyncio
async def test_search_matches_substring_in_cyrillic_name(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # регистр совпадает намеренно: sqlite сравнивает без учёта регистра только латиницу
    await create_customer(client, auth_headers, "АвиаТех")
    await create_customer(client, auth_headers, "Беспилотные системы")

    assert await list_names(client, auth_headers, "?q=виа") == ["АвиаТех"]


@pytest.mark.asyncio
async def test_search_without_matches_returns_empty_list(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await create_customer(client, auth_headers, "АвиаТех")

    assert await list_names(client, auth_headers, "?q=nothing-like-this") == []


@pytest.mark.asyncio
async def test_search_blank_q_is_ignored(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await create_customer(client, auth_headers, "Альфа")
    await create_customer(client, auth_headers, "Бета")

    assert await list_names(client, auth_headers, "?q=") == ["Альфа", "Бета"]
    assert await list_names(client, auth_headers, "?q=%20%20") == ["Альфа", "Бета"]


@pytest.mark.asyncio
async def test_search_treats_like_wildcards_literally(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """знаки % и _ в запросе — обычные символы, а не шаблон LIKE"""
    for name in ("Скидка 100%", "Скидка 1000", "A_B", "AxB"):
        await create_customer(client, auth_headers, name)

    assert await list_names(client, auth_headers, "?q=100%25") == ["Скидка 100%"]
    assert await list_names(client, auth_headers, "?q=A_B") == ["A_B"]


# --- Сортировка sort ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_sort_is_name_ascending(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    for name in ("гамма", "альфа", "бета"):
        await create_customer(client, auth_headers, name)

    expected = ["альфа", "бета", "гамма"]
    assert await list_names(client, auth_headers) == expected
    assert await list_names(client, auth_headers, "?sort=name") == expected


@pytest.mark.asyncio
async def test_sort_name_descending(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    for name in ("гамма", "альфа", "бета"):
        await create_customer(client, auth_headers, name)

    assert await list_names(client, auth_headers, "?sort=-name") == ["гамма", "бета", "альфа"]


@pytest.mark.asyncio
async def test_sort_with_unknown_field_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(f"{URL}?sort=email", headers=auth_headers)
    assert response.status_code == 422


# --- Пагинация ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination_limit_and_offset(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    for number in (3, 1, 5, 2, 4):
        await create_customer(client, auth_headers, f"заказчик {number}")

    assert await list_names(client, auth_headers, "?limit=2") == ["заказчик 1", "заказчик 2"]
    assert await list_names(client, auth_headers, "?limit=2&offset=2") == [
        "заказчик 3",
        "заказчик 4",
    ]
    assert await list_names(client, auth_headers, "?limit=2&offset=4") == ["заказчик 5"]
    assert await list_names(client, auth_headers, "?limit=2&offset=10") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["?limit=0", "?limit=101", "?offset=-1"])
async def test_pagination_invalid_params_return_422(
    client: AsyncClient, auth_headers: dict[str, str], query: str
) -> None:
    response = await client.get(f"{URL}{query}", headers=auth_headers)
    assert response.status_code == 422


# --- Права доступа -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customers_require_authentication(client: AsyncClient) -> None:
    response = await client.get(URL)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_viewer_can_read_customers(
    client: AsyncClient, auth_headers: dict[str, str], viewer_headers: dict[str, str]
) -> None:
    customer = await create_customer(client, auth_headers, "АвиаТех")

    listed = await client.get(URL, headers=viewer_headers)
    got = await client.get(f"{URL}/{customer['id']}", headers=viewer_headers)

    assert listed.status_code == 200
    assert got.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_create_customer(
    client: AsyncClient, viewer_headers: dict[str, str]
) -> None:
    response = await client.post(URL, headers=viewer_headers, json={"name": "АвиаТех"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_update_customer(
    client: AsyncClient, auth_headers: dict[str, str], viewer_headers: dict[str, str]
) -> None:
    customer = await create_customer(client, auth_headers, "АвиаТех")

    response = await client.patch(
        f"{URL}/{customer['id']}", headers=viewer_headers, json={"name": "другое"}
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_customer(
    client: AsyncClient, auth_headers: dict[str, str], viewer_headers: dict[str, str]
) -> None:
    customer = await create_customer(client, auth_headers, "АвиаТех")

    response = await client.delete(f"{URL}/{customer['id']}", headers=viewer_headers)

    assert response.status_code == 403
    # Заказчик остался на месте.
    still_there = await client.get(f"{URL}/{customer['id']}", headers=auth_headers)
    assert still_there.status_code == 200


# ураура я что-то сделал!
