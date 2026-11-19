from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ResourceCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    status: str = Field(default="declared", max_length=32)
    location: str | None = Field(default=None, max_length=512)
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    origin: dict[str, Any] = Field(default_factory=dict)


class ResourceUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version: int
    type: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=512)
    tags: list[str] | None = None
    attributes: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    origin: dict[str, Any] | None = None


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    type: str
    name: str
    status: str
    location: str | None
    tags: list[str]
    attributes: dict[str, Any]
    metadata: dict[str, Any] = Field(validation_alias="metadata_json")
    origin: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


class RelationshipCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_id: UUID
    target_id: UUID
    rel_type: str = Field(min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    source_id: UUID
    target_id: UUID
    rel_type: str
    metadata: dict[str, Any] = Field(validation_alias="metadata_json")
    created_at: datetime


class HistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_id: UUID
    version: int
    change_type: str
    actor: str
    source: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    delta: dict[str, Any] | None
    recorded_at: datetime


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
