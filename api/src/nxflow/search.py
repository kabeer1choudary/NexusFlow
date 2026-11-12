"""MVP search parser: whitespace-separated ``key:value`` predicates, ANDed together.

Supported keys:
    type, status, name, location, tag, attr.<key>, meta.<key>
Free-text (no colon) matches ``name ILIKE``.
"""

from __future__ import annotations

import json
import shlex
from typing import Any

from sqlalchemy import ColumnElement, or_

from .models import Resource


class SearchError(ValueError):
    pass


def tokenize(query: str) -> list[str]:
    try:
        return shlex.split(query)
    except ValueError as exc:
        raise SearchError(f"invalid query syntax: {exc}") from exc


def _parse_json_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def compile_clause(token: str) -> ColumnElement[bool]:
    if ":" not in token:
        return Resource.name.ilike(f"%{token}%")

    key, value = token.split(":", 1)
    if not key or value == "":
        raise SearchError(f"invalid token: {token!r}")

    if key == "type":
        return Resource.type == value
    if key == "status":
        return Resource.status == value
    if key == "name":
        return Resource.name.ilike(f"%{value}%")
    if key == "location":
        prefix = value[:-1] if value.endswith("*") else value
        return Resource.location.like(f"{prefix}%")
    if key == "tag":
        return Resource.tags.contains([value])
    if key.startswith("attr."):
        return Resource.attributes.contains({key[5:]: _parse_json_value(value)})
    if key.startswith("meta."):
        return Resource.metadata_json.contains({key[5:]: _parse_json_value(value)})

    raise SearchError(f"unknown search key: {key!r}")


def compile_query(query: str | None) -> list[ColumnElement[bool]]:
    if not query:
        return []
    tokens = tokenize(query)
    if not tokens:
        return []
    return [compile_clause(token) for token in tokens]


def text_search_clause(query: str) -> ColumnElement[bool]:
    pattern = f"%{query}%"
    return or_(Resource.name.ilike(pattern), Resource.location.ilike(pattern))
