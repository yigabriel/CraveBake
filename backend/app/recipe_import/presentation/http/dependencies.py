"""Wiring of the recipe-import module: the providers come from settings."""
from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import Depends

from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.ingredients.presentation.http.dependencies import get_ingredient_query_service
from app.recipe_import.application.use_cases.import_recipe_from_video_use_case import ImportRecipeFromVideoUseCase
from app.recipe_import.domain.services.ports import ImportCatalog, RecipeExtractor, VideoTextSource
from app.recipe_import.domain.video_text import ImportUnavailableError
from app.recipe_import.infrastructure.claude_recipe_extractor import ClaudeRecipeExtractor
from app.recipe_import.infrastructure.gemini_recipe_extractor import GeminiRecipeExtractor
from app.recipe_import.infrastructure.ingredients_module_catalog import IngredientsModuleCatalog
from app.recipe_import.infrastructure.supadata_video_text_source import SupadataVideoTextSource
from app.shared.config.settings import get_settings
from app.shared.presentation.request_rate_limiter import RequestRateLimiter

logger = logging.getLogger(__name__)


def get_video_text_source() -> VideoTextSource:
    key = get_settings().supadata_api_key
    if not key:
        # The client only sees a 503: say here what is missing (the value is never logged).
        logger.error("Recipe import unavailable: SUPADATA_API_KEY is not set in this environment")
        raise ImportUnavailableError()
    return SupadataVideoTextSource(key, min_interval=get_settings().supadata_min_interval_seconds)


def get_recipe_extractor() -> RecipeExtractor:
    settings = get_settings()
    if settings.import_extractor == "claude":
        if not settings.anthropic_api_key:
            logger.error("Recipe import unavailable: ANTHROPIC_API_KEY is not set in this environment")
            raise ImportUnavailableError()
        return ClaudeRecipeExtractor(settings.anthropic_api_key, settings.anthropic_model)
    if not settings.gemini_api_key:
        logger.error("Recipe import unavailable: GEMINI_API_KEY is not set in this environment")
        raise ImportUnavailableError()
    return GeminiRecipeExtractor(settings.gemini_api_key, settings.gemini_model)


def get_import_catalog(ingredients: IngredientQueryService = Depends(get_ingredient_query_service)) -> ImportCatalog:
    return IngredientsModuleCatalog(ingredients)


@lru_cache
def get_import_rate_limiter() -> RequestRateLimiter:
    settings = get_settings()
    return RequestRateLimiter(settings.import_max_requests, settings.import_window_seconds)


def get_import_recipe_use_case(
    source: VideoTextSource = Depends(get_video_text_source),
    extractor: RecipeExtractor = Depends(get_recipe_extractor),
    catalog: ImportCatalog = Depends(get_import_catalog),
) -> ImportRecipeFromVideoUseCase:
    return ImportRecipeFromVideoUseCase(source, extractor, catalog)
