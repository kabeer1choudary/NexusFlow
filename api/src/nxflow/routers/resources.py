from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_api_key
from ..db import get_session
from ..schemas import Page, ResourceCreate, ResourceRead, ResourceUpdate
from ..services import (
    create_resource,
    delete_resource,
    get_resource,
    list_resources,
    update_resource,
)

router = APIRouter(
    prefix="/api/v1/resources", tags=["resources"], dependencies=[Depends(require_api_key)]
)


@router.get("", response_model=Page[ResourceRead])
async def list_all(
    q: str | None = None,
    type: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    tag: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> Page[ResourceRead]:
    rows, total = await list_resources(
        session,
        q=q,
        type_=type,
        status_filter=status_filter,
        tag=tag,
        limit=limit,
        offset=offset,
    )
    return Page[ResourceRead](
        items=[ResourceRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ResourceRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: ResourceCreate, session: AsyncSession = Depends(get_session)
) -> ResourceRead:
    resource = await create_resource(session, payload)
    return ResourceRead.model_validate(resource)


@router.get("/{resource_id}", response_model=ResourceRead)
async def get_one(
    resource_id: UUID, session: AsyncSession = Depends(get_session)
) -> ResourceRead:
    return ResourceRead.model_validate(await get_resource(session, resource_id))


@router.patch("/{resource_id}", response_model=ResourceRead)
async def patch(
    resource_id: UUID,
    payload: ResourceUpdate,
    session: AsyncSession = Depends(get_session),
) -> ResourceRead:
    return ResourceRead.model_validate(await update_resource(session, resource_id, payload))


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(resource_id: UUID, session: AsyncSession = Depends(get_session)) -> Response:
    await delete_resource(session, resource_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
