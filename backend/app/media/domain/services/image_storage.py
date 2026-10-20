"""
ImageStorage — port towards wherever photos live (Supabase Storage today).

Swapping providers (R2, Cloudinary...) means writing another adapter for this
port; nothing else in the application changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SignedUpload:
    upload_url: str  # the browser PUTs the file here, once
    public_url: str  # where the photo is served from afterwards


class ImageStorage(ABC):
    @abstractmethod
    async def create_signed_upload(self, path: str) -> SignedUpload:
        """A single-use URL to upload the object at `path`."""
