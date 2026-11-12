from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_api_key
from ..db import get_session
from ..schemas import RelationshipCreate, RelationshipRead
from ..services import create_relationship, delete_relationship, list_relationships

router = APIRouter(
    prefix="/api/v1", tags=["relationships"], dependencies=[Depends(require_api_key)]
)


@router.post(
    "/relationships", response_model=RelationshipRead, status_code=status.HTTP_201_CREATED
)
async def create(
    payload: RelationshipCreate, session: AsyncSession = Depends(get_session)
) -> RelationshipRead:
    return RelationshipRead.model_validate(await create_relationship(session, payload))


@router.get("/resources/{resource_id}/relationships", response_model=list[RelationshipRead])
async def list_for_resource(
    resource_id: UUID, session: AsyncSession = Depends(get_session)
) -> list[RelationshipRead]:
    rows = await list_relationships(session, resource_id)
    return [RelationshipRead.model_validate(r) for r in rows]


@router.delete("/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    relationship_id: UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    await delete_relationship(session, relationship_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
