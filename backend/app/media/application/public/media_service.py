"""
MediaService — the media module's public API (Open Host Service) for other bounded contexts.

Other modules never touch storage or its rules directly: they hand over an image and get back
the URL to reference, exactly as if the person had uploaded it.
"""
from __future__ import annotations

from app.media.application.use_cases.store_image_use_case import StoreImageUseCase
from app.media.domain.upload_policy import ImagePurpose


class MediaService:
    def __init__(self, store_image: StoreImageUseCase) -> None:
        self._store_image = store_image

    async def store_recipe_photo(self, owner_user_id: str, content_type: str, data: bytes) -> str:
        """Stores a recipe photo in the owner's folder; raises the module's errors if it is not acceptable."""
        return await self._store_image.execute(owner_user_id, ImagePurpose.RECIPE, content_type, data)
