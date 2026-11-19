from __future__ import annotations

import pytest
from httpx import AsyncClient
from nxflow.db import get_engine
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


async def test_history_records_create_and_update(client: AsyncClient, resource_payload):
    created = (await client.post("/api/v1/resources", json=resource_payload)).json()
    patched = await client.patch(
        f"/api/v1/resources/{created['id']}",
        json={"version": 1, "status": "retired"},
        headers={"x-actor": "alice"},
    )
    assert patched.status_code == 200

    history = await client.get(f"/api/v1/resources/{created['id']}/history")
    assert history.status_code == 200
    rows = history.json()
    assert [r["change_type"] for r in rows] == ["update", "create"]
    assert rows[0]["actor"] == "alice"
    assert rows[0]["delta"]["status"] == {"before": "active", "after": "retired"}
    assert rows[1]["after"]["name"] == "web-01"


async def test_history_is_append_only(client: AsyncClient, resource_payload):
    await client.post("/api/v1/resources", json=resource_payload)
    engine = get_engine()
    with pytest.raises(DBAPIError):
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE resource_history SET actor = 'mallory'"))
    with pytest.raises(DBAPIError):
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM resource_history"))


async def test_delete_is_audited(client: AsyncClient, resource_payload):
    created = (await client.post("/api/v1/resources", json=resource_payload)).json()
    assert (await client.delete(f"/api/v1/resources/{created['id']}")).status_code == 204

    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT change_type FROM resource_history WHERE resource_id = :rid "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"rid": created["id"]},
        )
        assert result.scalar_one() == "delete"


async def test_history_404_for_unknown_resource(client: AsyncClient):
    response = await client.get("/api/v1/resources/00000000-0000-0000-0000-000000000000/history")
    assert response.status_code == 404
