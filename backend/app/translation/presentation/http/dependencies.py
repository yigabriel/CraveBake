"""Wiring of the translation module: the translator comes from settings."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from app.shared.config.settings import get_settings
from app.translation.application.use_cases.suggest_translations_use_case import SuggestTranslationsUseCase
from app.translation.domain.exceptions import TranslationUnavailableError
from app.translation.domain.services.text_translator import TextTranslator
from app.translation.infrastructure.azure_translator import AzureTranslator
from app.translation.infrastructure.google_cloud_translator import GoogleCloudTranslator
from app.shared.presentation.request_rate_limiter import RequestRateLimiter


def get_translator() -> TextTranslator:
    settings = get_settings()
    if settings.translation_provider == "google":
        if not settings.google_translate_api_key:
            raise TranslationUnavailableError()
        return GoogleCloudTranslator(settings.google_translate_api_key)
    if not settings.azure_translator_key or not settings.azure_translator_region:
        raise TranslationUnavailableError()
    return AzureTranslator(settings.azure_translator_key, settings.azure_translator_region, settings.azure_translator_endpoint)


@lru_cache
def get_translation_rate_limiter() -> RequestRateLimiter:
    settings = get_settings()
    return RequestRateLimiter(settings.translation_max_requests, settings.translation_window_seconds)


def get_suggest_translations_use_case(translator: TextTranslator = Depends(get_translator)) -> SuggestTranslationsUseCase:
    return SuggestTranslationsUseCase(translator)
