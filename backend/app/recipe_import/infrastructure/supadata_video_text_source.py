"""
Supadata adapter for `VideoTextSource` (https://docs.supadata.ai).

Two calls per video: the metadata (title, description, author: 1 credit) and the transcript in
`native` mode (only the captions the platform already has: 1 credit, and it never falls back to
transcribing audio, which would cost more). The key goes in a header, never the URL.

They are made one after the other, at least `min_interval` seconds apart, across every import in
the process: the free plan allows 1 request per second and answers 429 beyond it. A 429 is retried
(honouring `Retry-After`) before giving up.

The first request for a video can be slow (Supadata reads it from the platform then, and keeps it
afterwards): the timeout is generous, and a timed-out request is tried once more.

Supadata answers 206 when the video has no captions: that is normal, not an error — the recipe is
then read from the title and description alone.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

import httpx2

from app.recipe_import.domain.services.ports import VideoTextSource
from app.recipe_import.domain.source_url import SourceUrl
from app.recipe_import.domain.video_text import ImportUnavailableError, VideoText, VideoUnavailableError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.supadata.ai/v1"
MAX_RETRIES = 2
MAX_WAIT_SECONDS = 5.0
TIMEOUT_SECONDS = 60.0


class SupadataVideoTextSource(VideoTextSource):
    # When the next request may start. Shared by every instance: one process, one plan, one limit.
    _next_slot = 0.0

    def __init__(
        self,
        api_key: str,
        client: httpx2.AsyncClient | None = None,
        min_interval: float = 1.1,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._headers = {"x-api-key": api_key}
        self._client = client
        self._min_interval = min_interval
        self._clock = clock
        self._sleep = sleep

    async def fetch(self, source: SourceUrl) -> VideoText:
        try:
            metadata = await self._get("/metadata", {"url": source.url})
            info = self._metadata(metadata)  # a refusal here stops everything: no point paying for the second call
            transcript = await self._get("/transcript", {"url": source.url, "text": "true", "mode": "native"})
        except httpx2.HTTPError:
            logger.exception("Supadata unreachable")
            raise ImportUnavailableError()

        captions = self._captions(transcript)
        if info is None and captions is None and metadata.status_code in (403, 404) and transcript.status_code in (403, 404, 206):
            raise VideoUnavailableError()
        author = (info or {}).get("author") or {}
        return VideoText.clean(
            title=(info or {}).get("title"),
            description=(info or {}).get("description"),
            transcript=captions,
            author=author.get("displayName") or (f"@{author['username']}" if author.get("username") else None),
            thumbnail_url=((info or {}).get("media") or {}).get("thumbnailUrl"),
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
        """One request, spaced from the previous one; a 429 is waited out and retried."""
        timed_out = False
        for attempt in range(MAX_RETRIES + 1):
            await self._wait_for_slot()
            try:
                response = await self._send(path, params)
            except httpx2.TimeoutException:
                if timed_out:  # twice: give up (the caller turns it into "unavailable")
                    raise
                timed_out = True
                logger.warning("Supadata %s timed out; trying once more", path)
                continue
            if response.status_code != 429 or attempt == MAX_RETRIES:
                return response
            await self._sleep(self._retry_delay(response))
        raise httpx2.TimeoutException("Supadata kept timing out")

    async def _wait_for_slot(self) -> None:
        # Reserve the slot before sleeping, so imports that arrive together queue up instead of colliding.
        now = self._clock()
        slot = max(now, SupadataVideoTextSource._next_slot)
        SupadataVideoTextSource._next_slot = slot + self._min_interval
        if slot > now:
            await self._sleep(slot - now)

    def _retry_delay(self, response: httpx2.Response) -> float:
        try:
            asked = float(response.headers.get("retry-after", ""))
        except ValueError:
            asked = self._min_interval * 1.5
        return min(max(asked, self._min_interval), MAX_WAIT_SECONDS)

    async def _send(self, path: str, params: dict) -> httpx2.Response:
        if self._client is not None:
            return await self._client.get(f"{BASE_URL}{path}", params=params, headers=self._headers)
        async with httpx2.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            return await client.get(f"{BASE_URL}{path}", params=params, headers=self._headers)
