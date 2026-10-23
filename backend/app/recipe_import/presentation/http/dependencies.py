"""Wiring of the recipe-import module: the providers come from settings."""
from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import Depends

from app.equipment.application.public.equipment_query_service import EquipmentQueryService
from app.equipment.presentation.http.dependencies import get_equipment_query_service
from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.ingredients.presentation.http.dependencies import get_ingredient_query_service
from app.recipe_import.application.use_cases.import_recipe_from_video_use_case import ImportRecipeFromVideoUseCase
from app.media.application.public.media_service import MediaService
from app.media.presentation.http.dependencies import get_media_service
from app.recipe_import.domain.services.ports import CoverImageStore, ImportCatalog, RecipeExtractor, VideoTextSource
from app.recipe_import.domain.video_text import ImportUnavailableError
from app.recipe_import.infrastructure.claude_recipe_extractor import ClaudeRecipeExtractor
from app.recipe_import.infrastructure.gemini_recipe_extractor import GeminiRecipeExtractor
from app.recipe_import.infrastructure.modules_import_catalog import ModulesImportCatalog
from app.recipe_import.infrastructure.thumbnail_cover_store import ThumbnailCoverStore
from app.recipe_import.infrastructure.supadata_video_text_source import SupadataVideoTextSource
from app.recipes.application.public.recipe_query_service import RecipeQueryService
from app.recipes.presentation.http.dependencies import get_recipe_query_service
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


def get_import_catalog(
    ingredients: IngredientQueryService = Depends(get_ingredient_query_service),
    equipment: EquipmentQueryService = Depends(get_equipment_query_service),
    recipes: RecipeQueryService = Depends(get_recipe_query_service),
) -> ImportCatalog:
    return ModulesImportCatalog(ingredients, equipment, recipes)


def get_cover_store(media: MediaService | None = Depends(get_media_service)) -> CoverImageStore | None:
    """No storage configured: imports simply come without a cover."""
    return ThumbnailCoverStore(media) if media is not None else None


@lru_cache
def get_import_rate_limiter() -> RequestRateLimiter:
    settings = get_settings()
    return RequestRateLimiter(settings.import_max_requests, settings.import_window_seconds)


def get_import_recipe_use_case(
    source: VideoTextSource = Depends(get_video_text_source),
    extractor: RecipeExtractor = Depends(get_recipe_extractor),
    catalog: ImportCatalog = Depends(get_import_catalog),
    covers: CoverImageStore | None = Depends(get_cover_store),
) -> ImportRecipeFromVideoUseCase:
    return ImportRecipeFromVideoUseCase(source, extractor, catalog, covers)
