"""Pydantic schemas for the portfolio endpoints."""
from datetime import datetime

from pydantic import BaseModel
from app.shared.presentation.i18n import LocalizedStr


class PortfolioItemResponse(BaseModel):
    kind: str  # 'original' | 'personalized' | 'saved'
    recipe_id: str
    title: str
    description: str | None
    cover_photo_url: str | None
    category_name: LocalizedStr | None
    tags: list[LocalizedStr]
    difficulty_name: LocalizedStr | None
    prep_time_minutes: int | None
    servings: int | None
    is_public: bool
    created_by_user_id: str
    source_recipe_id: str | None
    source_recipe_title: str | None
    source_updated_since_personalized: bool | None
    added_at: datetime


class PortfolioSummaryResponse(BaseModel):
    original_count: int
    personalized_count: int
    saved_count: int
    total: int


class FavoriteStatusResponse(BaseModel):
    recipe_id: str
    is_saved: bool
    saved_at: datetime | None
