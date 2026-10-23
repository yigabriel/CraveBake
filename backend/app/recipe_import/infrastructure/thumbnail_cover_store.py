"""
`CoverImageStore` on top of the media module: copies a video's thumbnail into our storage.

The thumbnail URL comes from an external provider, and the server downloads it on the person's
behalf, so it is a door to guard (server-side request forgery):
- only https, only the image CDNs of TikTok and Instagram, no redirects (a redirect could lead anywhere);
- only JPEG/PNG/WebP (what a person could upload too), at most the upload limit, read in chunks so a
  huge answer is cut off instead of filling memory.

A copy is needed because the platforms' thumbnail links are signed and stop working after a while.
Everything here is best effort: any failure means "no cover", never a failed import.
"""
from __future__ import annotations

import logging
from urllib.parse import urlsplit

import httpx2

from app.media.application.public.media_service import MediaService
from app.media.domain.upload_policy import MAX_BYTES
from app.recipe_import.domain.services.ports import CoverImageStore
from app.shared.exceptions.domain_exceptions import DomainError

logger = logging.getLogger(__name__)

# The CDNs TikTok and Instagram serve thumbnails from (a host matches itself or any subdomain).
ALLOWED_HOST_SUFFIXES = (
    "tiktokcdn.com",
    "tiktokcdn-us.com",
    "tiktokcdn-eu.com",
    "ibyteimg.com",
    "byteimg.com",
    "muscdn.com",
    "cdninstagram.com",
    "fbcdn.net",
)
ACCEPTED_TYPES = ("image/jpeg", "image/png", "image/webp")


def is_allowed_thumbnail_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return False
    if parts.scheme != "https" or parts.username or parts.password or port not in (None, 443):
        return False
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in ALLOWED_HOST_SUFFIXES)


class ThumbnailCoverStore(CoverImageStore):
    def __init__(self, media: MediaService, client: httpx2.AsyncClient | None = None) -> None:
        self._media = media
        self._client = client

    async def store(self, image_url: str, owner_user_id: str) -> str | None:
        if not is_allowed_thumbnail_url(image_url):
            logger.warning("Thumbnail not copied: host not allowed (%s)", urlsplit(image_url).hostname)
            return None
        try:
            downloaded = await self._download(image_url)
            if downloaded is None:
                return None
            content_type, data = downloaded
            return await self._media.store_recipe_photo(owner_user_id, content_type, data)
        except (httpx2.HTTPError, DomainError):
            logger.exception("Thumbnail not copied")
            return None

    async def _download(self, url: str) -> tuple[str, bytes] | None:
        if self._client is not None:
            return await self._read(self._client, url)
        async with httpx2.AsyncClient(timeout=15, follow_redirects=False) as client:
            return await self._read(client, url)

    async def _read(self, client: httpx2.AsyncClient, url: str) -> tuple[str, bytes] | None:
        async with client.stream("GET", url, follow_redirects=False) as response:
            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if response.status_code != 200 or content_type not in ACCEPTED_TYPES:
                logger.warning("Thumbnail not copied: HTTP %s, %s", response.status_code, content_type or "no type")
                return None
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    logger.warning("Thumbnail not copied: larger than %s bytes", MAX_BYTES)
                    return None
        return content_type, bytes(data)
