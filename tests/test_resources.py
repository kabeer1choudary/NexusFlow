from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_healthz(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_and_get_resource(client: AsyncClient, resource_payload):
    created = await client.post("/api/v1/resources", json=resource_payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "web-01"
    assert body["metadata"]["asset_id"] == "A-1042"
    assert body["metadata"] and "metadata_json" not in body
    assert body["version"] == 1

    fetched = await client.get(f"/api/v1/resources/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


async def test_duplicate_resource_conflicts(client: AsyncClient, resource_payload):
    assert (await client.post("/api/v1/resources", json=resource_payload)).status_code == 201
    duplicate = await client.post("/api/v1/resources", json=resource_payload)
    assert duplicate.status_code == 409


async def test_patch_bumps_version(client: AsyncClient, resource_payload):
    created = (await client.post("/api/v1/resources", json=resource_payload)).json()
    patched = await client.patch(
        f"/api/v1/resources/{created['id']}",
        json={"version": 1, "status": "retired", "metadata": {"asset_id": "A-9999"}},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["status"] == "retired"
    assert body["metadata"] == {"asset_id": "A-9999"}
    assert body["version"] == 2


async def test_patch_version_conflict(client: AsyncClient, resource_payload):
    created = (await client.post("/api/v1/resources", json=resource_payload)).json()
    stale = await client.patch(
        f"/api/v1/resources/{created['id']}", json={"version": 99, "status": "retired"}
    )
    assert stale.status_code == 409


async def test_delete_resource(client: AsyncClient, resource_payload):
    created = (await client.post("/api/v1/resources", json=resource_payload)).json()
    assert (await client.delete(f"/api/v1/resources/{created['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/resources/{created['id']}")).status_code == 404


async def test_search_and_filters(client: AsyncClient, resource_payload):
    await client.post("/api/v1/resources", json=resource_payload)
    await client.post(
        "/api/v1/resources",
        json={**resource_payload, "name": "db-01", "tags": ["prod", "db"], "status": "declared"},
    )
    await client.post(
        "/api/v1/resources",
        json={**resource_payload, "name": "lab-01", "tags": ["lab"], "status": "retired"},
    )

    by_status = await client.get("/api/v1/resources", params={"q": "status:active"})
    assert by_status.status_code == 200
    assert by_status.json()["total"] == 1

    by_tag = await client.get("/api/v1/resources", params={"q": "tag:prod"})
    assert by_tag.json()["total"] == 2

    by_attr = await client.get("/api/v1/resources", params={"q": "attr.power:450"})
    assert by_attr.json()["total"] == 3

    by_location = await client.get("/api/v1/resources", params={"q": "location:dc1/row3"})
    assert by_location.json()["total"] == 3

    by_name = await client.get("/api/v1/resources", params={"q": "db-01"})
    assert by_name.json()["total"] == 1

    filtered = await client.get("/api/v1/resources", params={"status": "retired"})
    assert filtered.json()["total"] == 1


async def test_invalid_search_query_returns_422(client: AsyncClient):
    response = await client.get("/api/v1/resources", params={"q": "bogus:x"})
    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, 501])
async def test_limit_bounds(client: AsyncClient, limit: int):
    assert (await client.get("/api/v1/resources", params={"limit": limit})).status_code == 422
