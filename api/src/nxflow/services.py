from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Relationship, Resource, ResourceHistory
from .schemas import RelationshipCreate, ResourceCreate, ResourceUpdate
from .search import SearchError, compile_query

FIELD_MAP = {"metadata": "metadata_json"}


async def create_resource(session: AsyncSession, payload: ResourceCreate) -> Resource:
    resource = Resource(
        type=payload.type,
        name=payload.name,
        status=payload.status,
        location=payload.location,
        tags=payload.tags,
        attributes=payload.attributes,
        metadata_json=payload.metadata,
        origin=payload.origin,
        version=1,
    )
    session.add(resource)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"resource {payload.type}/{payload.name} already exists",
        ) from exc
    await session.refresh(resource)
    return resource


async def get_resource(session: AsyncSession, resource_id: UUID) -> Resource:
    resource = await session.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return resource


async def update_resource(
    session: AsyncSession, resource_id: UUID, payload: ResourceUpdate
) -> Resource:
    result = await session.execute(
        select(Resource).where(Resource.id == resource_id).with_for_update()
    )
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    if resource.version != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"version conflict: expected {resource.version}, got {payload.version}",
        )

    for field in payload.model_fields_set - {"version"}:
        attr = FIELD_MAP.get(field, field)
        value = getattr(payload, field)
        if value is None:
            if attr in {"type", "name", "status"}:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field} cannot be null",
                )
            if attr == "tags":
                value = []
            elif attr in {"attributes", "metadata_json", "origin"}:
                value = {}
        setattr(resource, attr, value)
    resource.version += 1

    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="resource type/name must be unique"
        ) from exc
    await session.refresh(resource)
    return resource


async def delete_resource(session: AsyncSession, resource_id: UUID) -> None:
    resource = await get_resource(session, resource_id)
    await session.delete(resource)
    await session.flush()


async def list_resources(
    session: AsyncSession,
    *,
    q: str | None = None,
    type_: str | None = None,
    status_filter: str | None = None,
    tag: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Resource], int]:
    try:
        clauses = compile_query(q)
    except SearchError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None
    if type_:
        clauses.append(Resource.type == type_)
    if status_filter:
        clauses.append(Resource.status == status_filter)
    if tag:
        clauses.append(Resource.tags.contains([tag]))

    total = await session.scalar(select(func.count()).select_from(Resource).where(*clauses))
    rows = (
        await session.scalars(
            select(Resource)
            .where(*clauses)
            .order_by(Resource.created_at.desc(), Resource.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(rows), int(total or 0)


async def list_history(
    session: AsyncSession, resource_id: UUID, *, limit: int = 100, offset: int = 0
) -> list[ResourceHistory]:
    await get_resource(session, resource_id)
    rows = (
        await session.scalars(
            select(ResourceHistory)
            .where(ResourceHistory.resource_id == resource_id)
            .order_by(ResourceHistory.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(rows)


async def create_relationship(
    session: AsyncSession, payload: RelationshipCreate
) -> Relationship:
    await get_resource(session, payload.source_id)
    await get_resource(session, payload.target_id)
    relationship = Relationship(
        source_id=payload.source_id,
        target_id=payload.target_id,
        rel_type=payload.rel_type,
        metadata_json=payload.metadata,
    )
    session.add(relationship)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="relationship already exists"
        ) from exc
    await session.refresh(relationship)
    return relationship


async def list_relationships(session: AsyncSession, resource_id: UUID) -> list[Relationship]:
    await get_resource(session, resource_id)
    rows = (
        await session.scalars(
            select(Relationship)
            .where(
                (Relationship.source_id == resource_id) | (Relationship.target_id == resource_id)
            )
            .order_by(Relationship.created_at)
        )
    ).all()
    return list(rows)


async def delete_relationship(session: AsyncSession, relationship_id: UUID) -> None:
    relationship = await session.get(Relationship, relationship_id)
    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="relationship not found"
        )
    await session.delete(relationship)
    await session.flush()


async def import_resources(
    session: AsyncSession, payloads: list[ResourceCreate]
) -> list[Resource]:
    created: list[Resource] = []
    for payload in payloads:
        existing = await session.scalar(
            select(Resource.id).where(Resource.type == payload.type, Resource.name == payload.name)
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"resource {payload.type}/{payload.name} already exists",
            )
        resource = Resource(
            type=payload.type,
            name=payload.name,
            status=payload.status,
            location=payload.location,
            tags=payload.tags,
            attributes=payload.attributes,
            metadata_json=payload.metadata,
            origin=payload.origin,
            version=1,
        )
        session.add(resource)
        created.append(resource)
    await session.flush()
    for resource in created:
        await session.refresh(resource)
    return created


async def export_resources(session: AsyncSession, q: str | None = None) -> list[Resource]:
    try:
        clauses = compile_query(q)
    except SearchError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None
    rows = (
        await session.scalars(
            select(Resource).where(*clauses).order_by(Resource.type, Resource.name)
        )
    ).all()
    return list(rows)
