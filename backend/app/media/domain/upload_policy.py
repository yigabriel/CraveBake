"""
What may be uploaded, and where it goes.

Photos are uploaded by the browser straight to object storage with a signed,
single-use URL; the API only decides *what* may be uploaded and *where*. The
client already shrinks photos to WebP before uploading; these limits are the
server-side guarantee.
"""
from __future__ import annotations

import uuid
from enum import Enum

from app.shared.exceptions.domain_exceptions import ServiceUnavailableError, ValidationError

MAX_BYTES = 5 * 1024 * 1024
_EXTENSIONS = {"image/webp": "webp", "image/jpeg": "jpg", "image/png": "png"}


class ImagePurpose(str, Enum):
    RECIPE = "recipe"  # cover and step photos
    AVATAR = "avatar"

    @property
    def folder(self) -> str:
        return {ImagePurpose.RECIPE: "recipes", ImagePurpose.AVATAR: "avatars"}[self]


class UnsupportedImageTypeError(ValidationError):
    def __init__(self, content_type: str) -> None:
        allowed = ", ".join(_EXTENSIONS)
        super().__init__(f"'{content_type}' images are not accepted. Allowed: {allowed}")


class ImageStorageUnavailableError(ServiceUnavailableError):
    def __init__(self) -> None:
        super().__init__("Image uploads are not available right now")


def object_path(purpose: ImagePurpose, user_id: str, content_type: str) -> str:
    """A fresh, unguessable path per upload, grouped by purpose and owner: recipes/<user>/<uuid>.webp."""
    extension = _EXTENSIONS.get(content_type)
    if extension is None:
        raise UnsupportedImageTypeError(content_type)
    return f"{purpose.folder}/{user_id}/{uuid.uuid4().hex}.{extension}"
