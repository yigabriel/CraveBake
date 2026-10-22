"""
StoredImages — port to see and delete what is already in object storage.

Kept apart from `ImageStorage` (which only signs uploads): the request that
signs an upload has no business listing or deleting files (interface segregation).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class StoredImage:
    path: str
    created_at: datetime | None  # None: the storage did not say, so it is never treated as old


class StoredImages(ABC):
    @abstractmethod
    async def list_all(self) -> list[StoredImage]:
        """Every file in the bucket, folders already walked."""

    @abstractmethod
    async def delete(self, paths: list[str]) -> None:
        """Removes these files for good."""

    @abstractmethod
    def path_of(self, url: str) -> str | None:
        """The storage path a public URL points to; None for any other URL (an external link)."""
