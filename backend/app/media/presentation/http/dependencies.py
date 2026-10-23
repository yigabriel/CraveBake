"""Wiring of the media module: the storage adapter comes from settings."""
from __future__ import annotations

from fastapi import Depends

from app.media.application.public.media_service import MediaService
from app.media.application.use_cases.request_image_upload_use_case import RequestImageUploadUseCase
from app.media.application.use_cases.store_image_use_case import StoreImageUseCase
from app.media.domain.services.image_storage import ImageStorage
from app.media.domain.upload_policy import ImageStorageUnavailableError
from app.media.infrastructure.supabase_image_storage import SupabaseImageStorage
from app.shared.config.settings import get_settings


def get_image_storage() -> ImageStorage:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ImageStorageUnavailableError()
    return SupabaseImageStorage(settings.supabase_url, settings.supabase_service_key, settings.supabase_storage_bucket)


def get_media_service() -> MediaService | None:
    """For other modules. None when storage is not configured: for them a photo is optional, not an error."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        return None
    storage = SupabaseImageStorage(settings.supabase_url, settings.supabase_service_key, settings.supabase_storage_bucket)
    return MediaService(StoreImageUseCase(storage))


def get_request_image_upload_use_case(storage: ImageStorage = Depends(get_image_storage)) -> RequestImageUploadUseCase:
    return RequestImageUploadUseCase(storage)
