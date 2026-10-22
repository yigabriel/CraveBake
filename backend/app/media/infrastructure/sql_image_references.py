"""
ImageReferences read straight from the tables that store image URLs.

This is a deliberate, read-only look across module boundaries: finding garbage
needs the whole picture, and asking each module for "your URLs" would just be the
same four SELECTs behind four more classes. The price is that a new column holding
an image URL must be added to `COLUMNS`; a test fails if one is missing.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.media.domain.services.image_references import ImageReferences

# (table, column) of every place an image URL is stored.
COLUMNS: tuple[tuple[str, str], ...] = (
    ("recipe_photos", "photo_url"),  # covers and step photos
    ("users", "avatar_url"),
    ("preparation_steps", "photo_url"),  # a preparation keeps its own copy of the step photos
    ("preparation_sessions", "cover_photo_url"),
)


class SqlImageReferences(ImageReferences):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def urls(self) -> set[str]:
        urls: set[str] = set()
        for table, column in COLUMNS:
            rows = await self._session.execute(text(f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL"))
            urls.update(rows.scalars().all())
        return urls
