"""
Gemini adapter for `RecipeExtractor` (Google AI, Interactions API with a JSON schema).

The prompt, the schema and the cleaning of the answer are shared with the other model adapters
(`extraction_schema`); this file only knows how to talk to Google. The API key goes in a header.
The model id comes from settings, since Google retires models.

Google's schema dialect is a subset of JSON Schema, so `additionalProperties` (which Claude's
structured outputs require) is left out; the answer is parsed defensively either way.
"""
from __future__ import annotations

import copy
import json
import logging
from typing import Any

import httpx2

from app.recipe_import.domain.extracted_recipe import ExtractedRecipe
from app.recipe_import.domain.services.ports import RecipeExtractor
from app.recipe_import.domain.video_text import ImportUnavailableError, VideoText
from app.recipe_import.infrastructure.extraction_schema import SCHEMA, SYSTEM_PROMPT, parse_recipe, user_message

logger = logging.getLogger(__name__)

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _without_additional_properties(node: Any) -> Any:
    if isinstance(node, dict):
        return {key: _without_additional_properties(value) for key, value in node.items() if key != "additionalProperties"}
    if isinstance(node, list):
        return [_without_additional_properties(value) for value in node]
    return node


GEMINI_SCHEMA = _without_additional_properties(copy.deepcopy(SCHEMA))


class GeminiRecipeExtractor(RecipeExtractor):
    def __init__(self, api_key: str, model: str, client: httpx2.AsyncClient | None = None) -> None:
        self._headers = {"x-goog-api-key": api_key}
        self._model = model
        self._client = client

    async def extract(self, text: VideoText, ingredient_names: list[str], unit_abbreviations: list[str]) -> ExtractedRecipe:
        body = {
            "model": self._model,
            "input": f"{SYSTEM_PROMPT}\n\n{user_message(text, ingredient_names, unit_abbreviations)}",
            "response_format": {"type": "text", "mime_type": "application/json", "schema": GEMINI_SCHEMA},
        }
        try:
            response = await self._post(body)
        except httpx2.HTTPError:
            logger.exception("Gemini unreachable")
            raise ImportUnavailableError()
        if response.status_code >= 400:
            # Never echo Google's answer to the client: it may describe the project.
            logger.error("Gemini refused the request (%s): %s", response.status_code, response.text[:300])
            raise ImportUnavailableError()
        try:
            answer = json.loads(_text_of(response.json()))
            if not isinstance(answer, dict):
                raise ValueError("the model did not answer with an object")
            return parse_recipe(answer)
        except (ValueError, TypeError, KeyError):
            logger.error("Unexpected answer from Gemini: %s", response.text[:500])
            raise ImportUnavailableError()

    async def _post(self, body: dict) -> httpx2.Response:
        if self._client is not None:
            return await self._client.post(URL, headers=self._headers, json=body)
        async with httpx2.AsyncClient(timeout=60) as client:
            return await client.post(URL, headers=self._headers, json=body)


def _text_of(payload: Any) -> str:
    """The model's text inside Google's envelope, whichever shape the API answered with.

    Interactions answers with `output_text` (or a list of outputs holding `text`); the older
    generateContent shape nests it in `candidates[].content.parts[].text`. Both are accepted.
    """
    if isinstance(payload, dict):
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        for key in ("outputs", "candidates", "content", "parts", "steps"):
            found = _first_text(payload.get(key))
            if found:
                return found
    raise ValueError("no text in the answer")


def _first_text(node: Any) -> str | None:
    if isinstance(node, dict):
        if isinstance(node.get("text"), str):
            return node["text"]
        for value in node.values():
            found = _first_text(value)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _first_text(value)
            if found:
                return found
    return None
