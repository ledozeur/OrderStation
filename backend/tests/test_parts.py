import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_part(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {
        "sku": "FRAME-X500",
        "name": "Рама карбоновая X500",
        "unit": "шт",
        "category": "Рамы",
    }
    resp = await client.post("/api/v1/parts", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["sku"] == "FRAME-X500"
    assert data["name"] == "Рама карбоновая X500"
    assert data["is_active"] is True
    part_id = data["id"]

    get_resp = await client.get(f"/api/v1/parts/{part_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == part_id


@pytest.mark.asyncio
async def test_create_duplicate_sku_conflict(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {"sku": "DUP-001", "name": "Мотор 1"}
    r1 = await client.post("/api/v1/parts", json=payload, headers=auth_headers)
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/parts", json={"sku": "DUP-001", "name": "Мотор 2"}, headers=auth_headers
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_get_part_not_found(client: AsyncClient, auth_headers: dict[str, str]):
    random_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/parts/{random_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_parts_search_and_inactive_filter(
    client: AsyncClient, auth_headers: dict[str, str]
):
    await client.post(
        "/api/v1/parts", json={"sku": "ESC-40A", "name": "Регулятор 40A"}, headers=auth_headers
    )
    r_del = await client.post(
        "/api/v1/parts", json={"sku": "PROP-1045", "name": "Пропеллер 1045"}, headers=auth_headers
    )
    del_id = r_del.json()["id"]

    # Архивируем вторую запчасть (soft delete)
    del_resp = await client.delete(f"/api/v1/parts/{del_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # По умолчанию неактивные скрыты
    list_active = await client.get("/api/v1/parts", headers=auth_headers)
    skus_active = [item["sku"] for item in list_active.json()]
    assert "ESC-40A" in skus_active
    assert "PROP-1045" not in skus_active

    # С include_inactive=true архивная запчасть видна
    list_all = await client.get("/api/v1/parts?include_inactive=true", headers=auth_headers)
    skus_all = [item["sku"] for item in list_all.json()]
    assert "PROP-1045" in skus_all

    # Поиск по q
    search_resp = await client.get("/api/v1/parts?q=40A", headers=auth_headers)
    assert len(search_resp.json()) == 1
    assert search_resp.json()[0]["sku"] == "ESC-40A"


@pytest.mark.asyncio
async def test_update_part_and_sku_conflict(client: AsyncClient, auth_headers: dict[str, str]):
    r1 = await client.post(
        "/api/v1/parts", json={"sku": "BAT-4S", "name": "АКБ 4S"}, headers=auth_headers
    )
    await client.post(
        "/api/v1/parts", json={"sku": "BAT-6S", "name": "АКБ 6S"}, headers=auth_headers
    )
    id1 = r1.json()["id"]

    # Успешное обновление названия
    patch_ok = await client.patch(
        f"/api/v1/parts/{id1}", json={"name": "АКБ LiPo 4S"}, headers=auth_headers
    )
    assert patch_ok.status_code == 200
    assert patch_ok.json()["name"] == "АКБ LiPo 4S"

    # Попытка сменить sku на уже занятый -> 409
    patch_conflict = await client.patch(
        f"/api/v1/parts/{id1}", json={"sku": "BAT-6S"}, headers=auth_headers
    )
    assert patch_conflict.status_code == 409


@pytest.mark.asyncio
async def test_parts_unauthorized(client: AsyncClient):
    resp = await client.get("/api/v1/parts")
    assert resp.status_code == 401
