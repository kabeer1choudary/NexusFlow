from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from . import __version__
from .db import dispose_engine, get_engine
from .routers import history, io, relationships, resources


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(title="NexusFlow", version=__version__, lifespan=lifespan)
    app.include_router(resources.router)
    app.include_router(relationships.router)
    app.include_router(history.router)
    app.include_router(io.router)

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
