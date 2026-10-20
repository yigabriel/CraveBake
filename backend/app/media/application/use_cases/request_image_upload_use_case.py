"""
RequestImageUploadUseCase — hands the browser a single-use URL to upload one photo.

The photo is not attached to anything yet: once uploaded, the client registers
its `public_url` where it belongs (a recipe cover, a step, the avatar) through
those modules' own endpoints, which keep their own rules (ownership, 3 covers...).
"""
from __future__ import annotations

from app.media.application.dto.image_upload_dto import ImageUploadDTO, RequestImageUploadDTO
from app.media.domain.services.image_storage import ImageStorage
from app.media.domain.upload_policy import MAX_BYTES, ImagePurpose, object_path


class RequestImageUploadUseCase:
    def __init__(self, storage: ImageStorage) -> None:
        self._storage = storage

    async def execute(self, dto: RequestImageUploadDTO) -> ImageUploadDTO:
        path = object_path(ImagePurpose(dto.purpose), dto.user_id, dto.content_type)
        signed = await self._storage.create_signed_upload(path)
        return ImageUploadDTO(
            upload_url=signed.upload_url,
            public_url=signed.public_url,
            content_type=dto.content_type,
            max_bytes=MAX_BYTES,
        )
