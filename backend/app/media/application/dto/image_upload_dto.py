"""DTOs of the image upload use case."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestImageUploadDTO:
    user_id: str
    purpose: str  # recipe | avatar
    content_type: str


@dataclass(frozen=True)
class ImageUploadDTO:
    upload_url: str
    public_url: str
    content_type: str
    max_bytes: int
