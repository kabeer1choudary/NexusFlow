from __future__ import annotations

from httpx import AsyncClient


async def _create(client: AsyncClient, payload: dict, name: str) -> str:
    response = await client.post("/api/v1/resources", json={**payload, "name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_relationship_lifecycle(client: AsyncClient, resource_payload):
    server = await _create(client, resource_payload, "web-01")
    rack = await _create(client, {**resource_payload, "type": "rack"}, "rack-7")

    created = await client.post(
        "/api/v1/relationships",
        json={
            "source_id": server,
            "target_id": rack,
            "rel_type": "racks",
            "metadata": {"slot": 3},
        },
    )
    assert created.status_code == 201, created.text
    edge = created.json()
    assert edge["metadata"] == {"slot": 3}
    assert edge["rel_type"] == "racks"

    listed = await client.get(f"/api/v1/resources/{server}/relationships")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    duplicate = await client.post(
        "/api/v1/relationships",
        json={"source_id": server, "target_id": rack, "rel_type": "racks"},
    )
    assert duplicate.status_code == 409

    assert (await client.delete(f"/api/v1/relationships/{edge['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/resources/{server}/relationships")).json() == []


async def test_relationship_requires_existing_resources(client: AsyncClient, resource_payload):
    server = await _create(client, resource_payload, "web-01")
    response = await client.post(
        "/api/v1/relationships",
        json={
            "source_id": server,
            "target_id": "00000000-0000-0000-0000-000000000000",
            "rel_type": "powers",
        },
    )
    assert response.status_code == 404
