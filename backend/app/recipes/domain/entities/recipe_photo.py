"""
RecipePhoto — a photo registered by URL (there is no file upload yet).

A `cover` photo belongs to the recipe's carousel and has no step; a `step`
photo illustrates exactly one preparation step. The limits (max 3 covers,
max 1 photo per step) are enforced by the `Recipe` aggregate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.recipes.domain.value_objects.recipe_photo_id import RecipePhotoId
from app.recipes.domain.value_objects.recipe_step_id import RecipeStepId
from app.shared.exceptions.domain_exceptions import ValidationError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PhotoType(str, Enum):
    COVER = "cover"
    STEP = "step"


@dataclass
class RecipePhoto:
    id: RecipePhotoId
    photo_type: PhotoType
    photo_url: str
    position: int = 0
    step_id: RecipeStepId | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.photo_url = validate_http_url(self.photo_url, "Photo URL")
        if self.photo_type == PhotoType.STEP and self.step_id is None:
            raise ValidationError("A step photo must reference a step")
        if self.photo_type == PhotoType.COVER and self.step_id is not None:
            raise ValidationError("A cover photo cannot reference a step")


def validate_http_url(raw: str, label: str) -> str:
    cleaned = (raw or "").strip()
    if not cleaned.startswith(("http://", "https://")) or len(cleaned) <= len("https://"):
        raise ValidationError(f"{label} must be a valid http(s) URL")
    return cleaned
