"""
SuggestTranslationsUseCase.

Translates a catalog name into every other language the app speaks. It only
*suggests*: nothing is stored here. The user reviews (and may edit) the
suggestions, and the translations are saved together with the new ingredient
or equipment through their own create endpoints.
"""
from __future__ import annotations

from app.shared.domain.value_objects.localized_text import SUPPORTED_LANGUAGES
from app.shared.exceptions.domain_exceptions import ValidationError
from app.translation.application.dto.translation_dto import SuggestTranslationsDTO
from app.translation.domain.services.text_translator import TextTranslator


class SuggestTranslationsUseCase:
    def __init__(self, translator: TextTranslator) -> None:
        self._translator = translator

    async def execute(self, dto: SuggestTranslationsDTO) -> dict[str, str]:
        """language -> suggested text, for every supported language except the source."""
        text = dto.text.strip()
        if not text:
            raise ValidationError("There is nothing to translate")
        if dto.source not in SUPPORTED_LANGUAGES:
            raise ValidationError(f"Unsupported language: {dto.source}")

        suggestions: dict[str, str] = {}
        for target in SUPPORTED_LANGUAGES:
            if target != dto.source:
                suggestions[target] = (await self._translator.translate(text, dto.source, target)).strip()
        return suggestions
