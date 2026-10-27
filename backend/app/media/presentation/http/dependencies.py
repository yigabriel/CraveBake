"""Wiring of the media module: the storage adapter comes from settings."""
from __future__ import annotations

from fastapi import Depends

from app.media.application.public.media_service import MediaService
from app.media.application.use_cases.request_image_upload_use_case import RequestImageUploadUseCase
from app.media.application.use_cases.store_image_use_case import StoreImageUseCase
from app.media.domain.services.image_storage import ImageStorage
from app.media.domain.upload_policy import ImageStorageUnavailableError
from app.media.infrastructure.configured_storage import configured_image_storage


def get_image_storage() -> ImageStorage:
    storage = configured_image_storage()
    if storage is None:
        raise ImageStorageUnavailableError()
    return storage


def get_media_service() -> MediaService | None:
    """For other modules. None when storage is not configured: for them a photo is optional, not an error."""
    storage = configured_image_storage()
    if storage is None:
        return None
    return MediaService(StoreImageUseCase(storage))


def get_request_image_upload_use_case(storage: ImageStorage = Depends(get_image_storage)) -> RequestImageUploadUseCase:
    return RequestImageUploadUseCase(storage)
