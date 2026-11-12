from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from nxflow import db
from nxflow.db_sql import TRIGGER_STATEMENTS
from nxflow.main import create_app
from nxflow.models import Base
from sqlalchemy.ext.asyncio import create_async_engine


def _normalize(url: str) -> str:
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix) :]
    return url


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    provided = os.getenv("NXFLOW_TEST_DATABASE_URL")
    if provided:
        yield _normalize(provided)
        return

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as pg:
        yield _normalize(pg.get_connection_url())


@pytest_asyncio.fixture
async def client(postgres_url: str) -> AsyncIterator[AsyncClient]:
    from nxflow.config import settings

    settings.database_url = postgres_url
    settings.api_key = None
    await db.dispose_engine()

    engine = create_async_engine(postgres_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        for statement in TRIGGER_STATEMENTS:
            await conn.exec_driver_sql(statement)
    await engine.dispose()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http

    await db.dispose_engine()


@pytest.fixture
def resource_payload() -> dict:
    return {
        "type": "server",
        "name": "web-01",
        "status": "active",
        "location": "dc1/row3/rack7",
        "tags": ["prod", "web"],
        "attributes": {"cpu": 32, "power": 450},
        "metadata": {"warranty": "2027-01-01", "asset_id": "A-1042"},
        "origin": {"source": "manual", "ref": None},
    }
