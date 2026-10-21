"""
Google Cloud Translation (Basic, v2) adapter for `TextTranslator`.

The API key stays on the server. It goes in the `X-goog-api-key` header rather
than the URL, so it never shows up in access logs or error messages.
"""
from __future__ import annotations

import logging

import httpx2

from app.translation.domain.exceptions import TranslationUnavailableError
from app.translation.domain.services.text_translator import TextTranslator

logger = logging.getLogger(__name__)

URL = "https://translation.googleapis.com/language/translate/v2"


class GoogleCloudTranslator(TextTranslator):
    def __init__(self, api_key: str, client: httpx2.AsyncClient | None = None) -> None:
        self._headers = {"X-goog-api-key": api_key}
        self._client = client

    async def translate(self, text: str, source: str, target: str) -> str:
        # format=text: the answer comes back as plain text, not HTML-escaped ("&#39;").
        body = {"q": text, "source": source, "target": target, "format": "text"}
        try:
            response = await self._post(body)
        except httpx2.HTTPError:
            logger.exception("Google Cloud Translation unreachable")
            raise TranslationUnavailableError()
        if response.status_code >= 400:
            # Never echo Google's answer to the client: it may describe the project setup.
            logger.error("Google Cloud Translation refused the request (%s): %s", response.status_code, response.text[:300])
            raise TranslationUnavailableError()
        try:
            return response.json()["data"]["translations"][0]["translatedText"]
        except (KeyError, IndexError, TypeError, ValueError):
            logger.error("Unexpected answer from Google Cloud Translation: %s", response.text[:300])
            raise TranslationUnavailableError()

    async def _post(self, body: dict) -> httpx2.Response:
        if self._client is not None:
            return await self._client.post(URL, headers=self._headers, json=body)
        async with httpx2.AsyncClient(timeout=10) as client:
            return await client.post(URL, headers=self._headers, json=body)
