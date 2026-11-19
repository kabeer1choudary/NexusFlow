from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_api_key
from ..db import get_session
from ..schemas import HistoryRead
from ..services import list_history

router = APIRouter(
    prefix="/api/v1/resources", tags=["history"], dependencies=[Depends(require_api_key)]
)


@router.get("/{resource_id}/history", response_model=list[HistoryRead])
async def history(
    resource_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[HistoryRead]:
    rows = await list_history(session, resource_id, limit=limit, offset=offset)
    return [HistoryRead.model_validate(r) for r in rows]
