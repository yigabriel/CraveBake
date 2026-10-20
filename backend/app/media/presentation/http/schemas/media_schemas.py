"""Pydantic schemas for the photo upload endpoint."""
from typing import Literal

from pydantic import BaseModel, Field


class RequestImageUploadRequest(BaseModel):
    purpose: Literal["recipe", "avatar"] = Field(description="recipe: cover and step photos; avatar: profile photo")
    content_type: Literal["image/webp", "image/jpeg", "image/png"]


class ImageUploadResponse(BaseModel):
    upload_url: str = Field(description="PUT the file here, once, with this Content-Type (valid ~2 hours)")
    public_url: str = Field(description="Where the photo is served from once uploaded: register it where it belongs")
    content_type: str
    max_bytes: int
