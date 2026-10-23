"""
StoreImageUseCase — keeps a copy of an image the server already holds, under the same rules as a
browser upload: an accepted type, at most MAX_BYTES, a fresh path in the owner's folder.
"""
from __future__ import annotations

from app.media.domain.services.image_uploader import ImageUploader
from app.media.domain.upload_policy import MAX_BYTES, ImagePurpose, ImageTooLargeError, object_path


class StoreImageUseCase:
    def __init__(self, uploader: ImageUploader) -> None:
        self._uploader = uploader

    async def execute(self, owner_user_id: str, purpose: ImagePurpose, content_type: str, data: bytes) -> str:
        if len(data) > MAX_BYTES:
            raise ImageTooLargeError()
        path = object_path(purpose, owner_user_id, content_type)  # rejects any type a browser could not upload either
        return await self._uploader.upload(path, data, content_type)
