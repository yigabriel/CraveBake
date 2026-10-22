"""
Claude adapter for `RecipeExtractor` (the official Anthropic SDK, Messages API).

The simplest model is enough for this: reading a caption and filling a fixed form. Haiku 5.5 at low
effort, with `output_config.format` so the API itself guarantees valid JSON of the schema's shape.
Haiku 5.5 takes no `temperature`/`top_p`/`top_k` and no prefill, so none are sent; the rules live in
the system prompt and the video text goes in the user turn as data.

Nothing the SDK or the API raises is shown to the client: it is logged here (never the key) and
the import simply answers "unavailable".
"""
from __future__ import annotations

import json
import logging

import anthropic

from app.recipe_import.domain.extracted_recipe import ExtractedRecipe
from app.recipe_import.domain.services.ports import ExtractionCatalog, RecipeExtractor
from app.recipe_import.domain.video_text import ImportUnavailableError, VideoText
from app.recipe_import.infrastructure.extraction_schema import SCHEMA, SYSTEM_PROMPT, parse_recipe, user_message

logger = logging.getLogger(__name__)

# Thinking counts toward max_tokens: leave room for it on top of a full recipe (80 lines + 60 steps).
MAX_TOKENS = 8000


class ClaudeRecipeExtractor(RecipeExtractor):
    def __init__(self, api_key: str, model: str, client: anthropic.AsyncAnthropic | None = None) -> None:
        # The SDK retries 408/409/429/5xx and connection errors twice by default; a request takes seconds, not minutes.
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key, timeout=60.0)
        self._model = model

    async def extract(self, text: VideoText, catalog: ExtractionCatalog) -> ExtractedRecipe:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message(text, catalog)}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            )
        except anthropic.APIStatusError as error:
            # 400 can be "credit balance too low"; 401/403 a bad or unauthorized key; 404 a wrong model id.
            logger.error("Claude refused the request (%s): %s", error.status_code, str(error.message)[:300])
            raise ImportUnavailableError()
        except anthropic.APIConnectionError:
            logger.exception("Claude unreachable")
            raise ImportUnavailableError()

        if response.stop_reason in ("refusal", "max_tokens"):
            logger.error("Claude stopped without an answer (stop_reason=%s)", response.stop_reason)
            raise ImportUnavailableError()
        # Read by type, not by position: a response can begin with thinking blocks.
        answer = next((block.text for block in response.content if block.type == "text"), None)
        try:
            data = json.loads(answer or "")
            if not isinstance(data, dict):
                raise ValueError("the model did not answer with an object")
        except ValueError:
            logger.error("Unexpected answer from Claude: %s", (answer or "")[:500])
            raise ImportUnavailableError()
        return parse_recipe(data)
