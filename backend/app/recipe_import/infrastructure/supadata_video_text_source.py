"""
Supadata adapter for `VideoTextSource` (https://docs.supadata.ai).

Two calls per video, made together: the metadata (title, description, author: 1 credit) and the
transcript in `native` mode (only the captions the platform already has: 1 credit, and it never
falls back to transcribing audio, which would cost more). The key goes in a header, never the URL.

Supadata answers 206 when the video has no captions: that is normal, not an error — the recipe is
then read from the title and description alone.
"""
from __future__ import annotations

import asyncio
import logging

import httpx2

from app.recipe_import.domain.services.ports import VideoTextSource
from app.recipe_import.domain.source_url import SourceUrl
from app.recipe_import.domain.video_text import ImportUnavailableError, VideoText, VideoUnavailableError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.supadata.ai/v1"


class SupadataVideoTextSource(VideoTextSource):
    def __init__(self, api_key: str, client: httpx2.AsyncClient | None = None) -> None:
        self._headers = {"x-api-key": api_key}
        self._client = client

    async def fetch(self, source: SourceUrl) -> VideoText:
        try:
            metadata, transcript = await asyncio.gather(
                self._get("/metadata", {"url": source.url}),
                self._get("/transcript", {"url": source.url, "text": "true", "mode": "native"}),
            )
        except httpx2.HTTPError:
            logger.exception("Supadata unreachable")
            raise ImportUnavailableError()

        info = self._metadata(metadata)
        captions = self._captions(transcript)
        if info is None and captions is None and metadata.status_code in (403, 404) and transcript.status_code in (403, 404, 206):
            raise VideoUnavailableError()
        author = (info or {}).get("author") or {}
        return VideoText.clean(
            title=(info or {}).get("title"),
            description=(info or {}).get("description"),
            transcript=captions,
            author=author.get("displayName") or (f"@{author['username']}" if author.get("username") else None),
        )

    def _metadata(self, response: httpx2.Response) -> dict | None:
        if response.status_code == 200:
            return response.json()
        self._check_provider_problem(response)
        return None

    def _captions(self, response: httpx2.Response) -> str | None:
        if response.status_code == 200:
            content = response.json().get("content")
            return content if isinstance(content, str) else None
        if response.status_code == 202:
            logger.warning("Supadata queued a native transcript as a job; skipping it")  # only for very long videos
            return None
        self._check_provider_problem(response)
        return None  # 206: the video has no captions

    @staticmethod
    def _check_provider_problem(response: httpx2.Response) -> None:
        """Our key or plan is the problem (not the video): tell the user it is unavailable, log the real cause."""
        if response.status_code in (401, 402, 429) or response.status_code >= 500:
            # Never echo the provider's answer to the client: it may describe the account.
            logger.error("Supadata refused the request (%s): %s", response.status_code, response.text[:300])
            raise ImportUnavailableError()

    async def _get(self, path: str, params: dict) -> httpx2.Response:
        if self._client is not None:
            return await self._client.get(f"{BASE_URL}{path}", params=params, headers=self._headers)
        async with httpx2.AsyncClient(timeout=30) as client:
            return await client.get(f"{BASE_URL}{path}", params=params, headers=self._headers)
