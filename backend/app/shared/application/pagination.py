"""
Generic page of results, shared by every bounded context.

Every collection that can grow (searches, "my recipes", portfolio...) is
returned as a `Page` so clients always get the same envelope: the items of
the requested window plus the total count before pagination.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
