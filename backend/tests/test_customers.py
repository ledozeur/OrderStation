import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_customer(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    create = await client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={"name": "АвиаТех", "contact_person": "Иванов"},
    )
    assert create.status_code == 201
    customer_id = create.json()["id"]

    listed = await client.get("/api/v1/customers", headers=auth_headers)
    assert listed.status_code == 200
    assert any(row["id"] == customer_id for row in listed.json())

    got = await client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["name"] == "АвиаТех"
