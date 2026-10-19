"""DTOs for the portfolio bounded context."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from app.shared.domain.value_objects.localized_text import LocalizedText


@dataclass(frozen=True)
class GetPortfolioDTO:
    user_id: str
    kind: str | None = None  # 'original' | 'personalized' | 'saved' | None (everything)
    query: str | None = None
    category_id: str | None = None
    tag_ids: list[str] = field(default_factory=list)  # recipe must have all of them
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class PortfolioItemDTO:
    kind: str
    recipe_id: str
    title: str
    description: str | None
    cover_photo_url: str | None
    category_name: LocalizedText | None
    tags: list[LocalizedText]
    difficulty_name: LocalizedText | None
    prep_time_minutes: int | None
    servings: int | None
    is_public: bool
    created_by_user_id: str
    source_recipe_id: str | None
    source_recipe_title: str | None
    source_updated_since_personalized: bool | None
    added_at: datetime


@dataclass(frozen=True)
class PortfolioSummaryDTO:
    original_count: int
    personalized_count: int
    saved_count: int
    total: int


@dataclass(frozen=True)
class FavoriteStatusDTO:
    recipe_id: str
    is_saved: bool
    saved_at: datetime | None
