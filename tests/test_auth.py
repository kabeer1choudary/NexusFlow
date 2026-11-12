from __future__ import annotations

from httpx import AsyncClient
from nxflow.config import settings


async def test_auth_disabled_without_key(client: AsyncClient):
    settings.api_key = None
    assert (await client.get("/api/v1/resources")).status_code == 200


async def test_auth_requires_valid_key(client: AsyncClient):
    settings.api_key = "secret"
    try:
        assert (await client.get("/api/v1/resources")).status_code == 401
        assert (
            await client.get("/api/v1/resources", headers={"x-api-key": "wrong"})
        ).status_code == 401
        assert (
            await client.get("/api/v1/resources", headers={"x-api-key": "secret"})
        ).status_code == 200
        assert (await client.get("/healthz")).status_code == 200
    finally:
        settings.api_key = None
