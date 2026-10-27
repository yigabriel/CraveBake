"""
Azure AI Translator (Text Translation v3) adapter for `TextTranslator`.

The key and the resource region go in headers, never in the URL, so they don't
show up in access logs or error messages.
"""
from __future__ import annotations

import logging

import httpx2

from app.translation.domain.exceptions import TranslationUnavailableError
from app.translation.domain.services.text_translator import TextTranslator

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://api.cognitive.microsofttranslator.com"


class AzureTranslator(TextTranslator):
    def __init__(
        self,
        api_key: str,
        region: str,
        endpoint: str = DEFAULT_ENDPOINT,
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        self._url = endpoint.rstrip("/") + "/translate"
        # A regional resource (e.g. brazilsouth) rejects requests without its region header.
        self._headers = {"Ocp-Apim-Subscription-Key": api_key, "Ocp-Apim-Subscription-Region": region}
        self._client = client

    async def translate(self, text: str, source: str, target: str) -> str:
        # textType=plain: plain text in and out, nothing HTML-escaped.
        params = {"api-version": "3.0", "from": source, "to": target, "textType": "plain"}
        try:
            response = await self._post(params, [{"Text": text}])
        except httpx2.HTTPError:
            logger.exception("Azure Translator unreachable")
            raise TranslationUnavailableError()
        if response.status_code >= 400:
            # Never echo Azure's answer to the client: it may describe the resource setup.
            logger.error("Azure Translator refused the request (%s): %s", response.status_code, response.text[:300])
            raise TranslationUnavailableError()
        try:
            return response.json()[0]["translations"][0]["text"]
        except (KeyError, IndexError, TypeError, ValueError):
            logger.error("Unexpected answer from Azure Translator: %s", response.text[:300])
            raise TranslationUnavailableError()

    async def _post(self, params: dict, body: list) -> httpx2.Response:
        if self._client is not None:
            return await self._client.post(self._url, params=params, headers=self._headers, json=body)
        async with httpx2.AsyncClient(timeout=10) as client:
            return await client.post(self._url, params=params, headers=self._headers, json=body)
