"""DTOs for the recommendations bounded context."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.shared.domain.value_objects.localized_text import LocalizedText


@dataclass(frozen=True)
class StartSessionDTO:
    user_id: str
    ingredient_ids: list[str]  # empty -> use the pantry
    min_score: float = 0.0
    category_id: str | None = None
    tag_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NamedRefDTO:
    id: str
    name: LocalizedText


@dataclass(frozen=True)
class DiscoverySessionDTO:
    id: str
    ingredient_source: str
    ingredients: list[NamedRefDTO]
    category: NamedRefDTO | None
    tags: list[NamedRefDTO]
    min_score: float
    discarded_count: int
    saved_count: int
    selected_count: int
    created_at: datetime


@dataclass(frozen=True)
class RecommendationDTO:
    recipe_id: str
    title: str
    description: str | None
    cover_photo_url: str | None
    category_name: LocalizedText | None
    difficulty_name: LocalizedText | None
    tags: list[LocalizedText]
    prep_time_minutes: int | None
    servings: int | None
    is_own: bool  # the user's own recipe or personalization: already in their portfolio, nothing to save
    is_personalization: bool
    source_recipe_title: str | None
    compatibility_score: float  # share of the recipe's ingredients the user has
    equipment_score: float
    rank_score: float
    matched_ingredients: list[NamedRefDTO]
    missing_ingredients: list[NamedRefDTO]
    missing_equipment: list[NamedRefDTO]
    has_all_equipment: bool
    is_saved: bool


@dataclass(frozen=True)
class SwipeDTO:
    id: str
    recipe_id: str
    action: str
    compatibility_score: float
    created_at: datetime
