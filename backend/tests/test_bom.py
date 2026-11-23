import uuid

import pytest
from httpx import AsyncClient


async def _create_part(client: AsyncClient, headers: dict[str, str], sku: str, name: str) -> str:
    resp = await client.post("/api/v1/parts", json={"sku": sku, "name": name}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_1_create_and_get_bom_template(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {
        "code": "UAV-X500",
        "name": "Квадрокоптер X500",
        "product_line": "X-Series",
        "version": "1.0",
    }
    resp = await client.post("/api/v1/bom-templates", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "UAV-X500"
    assert data["items"] == []

    get_resp = await client.get(f"/api/v1/bom-templates/{data['id']}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Квадрокоптер X500"


@pytest.mark.asyncio
async def test_2_create_duplicate_bom_code_conflict(
    client: AsyncClient, auth_headers: dict[str, str]
):
    payload = {"code": "DUP-BOM", "name": "Шаблон 1"}
    r1 = await client.post("/api/v1/bom-templates", json=payload, headers=auth_headers)
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/bom-templates", json={"code": "DUP-BOM", "name": "Шаблон 2"}, headers=auth_headers
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_3_get_bom_not_found(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.get(f"/api/v1/bom-templates/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_4_list_bom_templates_filter_and_search(
    client: AsyncClient, auth_headers: dict[str, str]
):
    await client.post(
        "/api/v1/bom-templates",
        json={"code": "BOM-ACT", "name": "Активный дрон", "is_active": True},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/bom-templates",
        json={"code": "BOM-ARC", "name": "Архивный дрон", "is_active": False},
        headers=auth_headers,
    )

    active_list = await client.get("/api/v1/bom-templates", headers=auth_headers)
    codes_active = [t["code"] for t in active_list.json()]
    assert "BOM-ACT" in codes_active
    assert "BOM-ARC" not in codes_active

    all_list = await client.get("/api/v1/bom-templates?include_inactive=true", headers=auth_headers)
    codes_all = [t["code"] for t in all_list.json()]
    assert "BOM-ARC" in codes_all

    search = await client.get("/api/v1/bom-templates?q=Активный", headers=auth_headers)
    assert len(search.json()) == 1
    assert search.json()[0]["code"] == "BOM-ACT"


@pytest.mark.asyncio
async def test_5_update_bom_template(client: AsyncClient, auth_headers: dict[str, str]):
    r1 = await client.post(
        "/api/v1/bom-templates", json={"code": "BOM-UPD-1", "name": "Старое"}, headers=auth_headers
    )
    await client.post(
        "/api/v1/bom-templates", json={"code": "BOM-UPD-2", "name": "Другой"}, headers=auth_headers
    )
    tpl_id = r1.json()["id"]

    ok = await client.patch(
        f"/api/v1/bom-templates/{tpl_id}",
        json={"name": "Новое имя", "version": "2.0"},
        headers=auth_headers,
    )
    assert ok.status_code == 200
    assert ok.json()["name"] == "Новое имя"
    assert ok.json()["version"] == "2.0"

    conflict = await client.patch(
        f"/api/v1/bom-templates/{tpl_id}", json={"code": "BOM-UPD-2"}, headers=auth_headers
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_6_delete_bom_template(client: AsyncClient, auth_headers: dict[str, str]):
    r = await client.post(
        "/api/v1/bom-templates",
        json={"code": "BOM-DEL", "name": "На удаление"},
        headers=auth_headers,
    )
    tpl_id = r.json()["id"]

    del_resp = await client.delete(f"/api/v1/bom-templates/{tpl_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/bom-templates/{tpl_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_7_add_bom_item_and_duplicate_conflict(
    client: AsyncClient, auth_headers: dict[str, str]
):
    part_id = await _create_part(client, auth_headers, "BOM-MOT-1", "Мотор BOM")
    r_tpl = await client.post(
        "/api/v1/bom-templates", json={"code": "BOM-ITEMS", "name": "Сборный"}, headers=auth_headers
    )
    tpl_id = r_tpl.json()["id"]

    item_resp = await client.post(
        f"/api/v1/bom-templates/{tpl_id}/items",
        json={"part_id": part_id, "quantity": 4, "note": "Лучевые моторы"},
        headers=auth_headers,
    )
    assert item_resp.status_code == 201
    assert float(item_resp.json()["quantity"]) == 4.0

    # Дубликат той же запчасти в одном шаблоне -> 409
    dup_resp = await client.post(
        f"/api/v1/bom-templates/{tpl_id}/items",
        json={"part_id": part_id, "quantity": 2},
        headers=auth_headers,
    )
    assert dup_resp.status_code == 409


@pytest.mark.asyncio
async def test_8_add_item_nonexistent_part_404(client: AsyncClient, auth_headers: dict[str, str]):
    r_tpl = await client.post(
        "/api/v1/bom-templates", json={"code": "BOM-NOPART", "name": "Тест"}, headers=auth_headers
    )
    tpl_id = r_tpl.json()["id"]

    resp = await client.post(
        f"/api/v1/bom-templates/{tpl_id}/items",
        json={"part_id": str(uuid.uuid4()), "quantity": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_9_update_and_delete_bom_item(client: AsyncClient, auth_headers: dict[str, str]):
    part_id = await _create_part(client, auth_headers, "BOM-ESC-1", "Регулятор BOM")
    r_tpl = await client.post(
        "/api/v1/bom-templates", json={"code": "BOM-ITEM-UPD", "name": "Тест"}, headers=auth_headers
    )
    tpl_id = r_tpl.json()["id"]

    r_item = await client.post(
        f"/api/v1/bom-templates/{tpl_id}/items",
        json={"part_id": part_id, "quantity": 4},
        headers=auth_headers,
    )
    item_id = r_item.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/bom-templates/{tpl_id}/items/{item_id}",
        json={"quantity": 6, "is_optional": True},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert float(patch_resp.json()["quantity"]) == 6.0
    assert patch_resp.json()["is_optional"] is True

    del_resp = await client.delete(
        f"/api/v1/bom-templates/{tpl_id}/items/{item_id}", headers=auth_headers
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_10_preview_bom_template(client: AsyncClient, auth_headers: dict[str, str]):
    p1 = await _create_part(client, auth_headers, "PRV-FRAME", "Рама X500")
    p2 = await _create_part(client, auth_headers, "PRV-PROP", "Пропеллер")

    r_tpl = await client.post(
        "/api/v1/bom-templates", json={"code": "BOM-PRV", "name": "Превью"}, headers=auth_headers
    )
    tpl_id = r_tpl.json()["id"]

    await client.post(
        f"/api/v1/bom-templates/{tpl_id}/items",
        json={"part_id": p1, "quantity": 1},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/bom-templates/{tpl_id}/items",
        json={"part_id": p2, "quantity": 4},
        headers=auth_headers,
    )

    # Превью на 3 изделия: 1*3 = 3 рамы, 4*3 = 12 пропеллеров
    prev_resp = await client.get(
        f"/api/v1/bom-templates/{tpl_id}/preview?quantity=3", headers=auth_headers
    )
    assert prev_resp.status_code == 200
    items = {row["sku"]: float(row["quantity"]) for row in prev_resp.json()}
    assert items == {"PRV-FRAME": 3.0, "PRV-PROP": 12.0}


@pytest.mark.asyncio
async def test_11_bom_unauthorized(client: AsyncClient):
    resp = await client.get("/api/v1/bom-templates")
    assert resp.status_code == 401
