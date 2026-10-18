"""HTTP schema for `Page` — the single pagination envelope of the API."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
