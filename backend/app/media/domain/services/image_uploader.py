"""
ImageUploader — port to store an image the server already holds (not one the browser uploads).

Used when the server itself fetched the picture (a video's thumbnail when a recipe is imported).
Kept apart from `ImageStorage`, which only signs browser uploads (interface segregation).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ImageUploader(ABC):
    @abstractmethod
    async def upload(self, path: str, data: bytes, content_type: str) -> str:
        """Stores `data` at `path`; returns the public URL it is served from."""
