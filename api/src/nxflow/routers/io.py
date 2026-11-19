from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_api_key
from ..db import get_session
from ..schemas import ResourceCreate, ResourceRead
from ..services import export_resources, import_resources

router = APIRouter(prefix="/api/v1", tags=["io"], dependencies=[Depends(require_api_key)])


@router.post(
    "/import", response_model=list[ResourceRead], status_code=status.HTTP_201_CREATED
)
async def import_json(
    payload: list[ResourceCreate], session: AsyncSession = Depends(get_session)
) -> list[ResourceRead]:
    rows = await import_resources(session, payload)
    return [ResourceRead.model_validate(r) for r in rows]


@router.get("/export", response_model=list[ResourceRead])
async def export_json(
    q: str | None = None, session: AsyncSession = Depends(get_session)
) -> list[ResourceRead]:
    rows = await export_resources(session, q=q)
    return [ResourceRead.model_validate(r) for r in rows]
