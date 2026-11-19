from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url, echo=settings.sql_echo, pool_pre_ping=True
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, autoflush=False
        )
    return _session_factory


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    actor = request.headers.get("x-actor", "api")
    source = request.headers.get("x-source", "api")
    async with get_session_factory()() as session:
        async with session.begin():
            await session.execute(
                text(
                    "SELECT set_config('nxflow.actor', :actor, true), "
                    "set_config('nxflow.source', :source, true)"
                ),
                {"actor": actor, "source": source},
            )
            yield session
