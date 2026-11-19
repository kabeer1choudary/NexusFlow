from __future__ import annotations

from httpx import AsyncClient


async def test_import_then_export_round_trip(client: AsyncClient, resource_payload):
    payload = [resource_payload, {**resource_payload, "name": "web-02"}]
    imported = await client.post("/api/v1/import", json=payload)
    assert imported.status_code == 201, imported.text
    assert len(imported.json()) == 2

    exported = await client.get("/api/v1/export")
    assert exported.status_code == 200
    assert {row["name"] for row in exported.json()} == {"web-01", "web-02"}
    assert exported.json()[0]["metadata"]["asset_id"] == "A-1042"


async def test_import_is_atomic_on_conflict(client: AsyncClient, resource_payload):
    await client.post("/api/v1/resources", json=resource_payload)
    response = await client.post(
        "/api/v1/import", json=[{**resource_payload, "name": "web-99"}, resource_payload]
    )
    assert response.status_code == 409
    assert (await client.get("/api/v1/resources", params={"q": "web-99"})).json()["total"] == 0


async def test_import_validation_error(client: AsyncClient):
    response = await client.post("/api/v1/import", json=[{"type": "server"}])
    assert response.status_code == 422


async def test_export_with_filter(client: AsyncClient, resource_payload):
    await client.post("/api/v1/resources", json=resource_payload)
    await client.post(
        "/api/v1/resources", json={**resource_payload, "name": "lab-01", "status": "retired"}
    )
    exported = await client.get("/api/v1/export", params={"q": "status:retired"})
    assert [row["name"] for row in exported.json()] == ["lab-01"]
