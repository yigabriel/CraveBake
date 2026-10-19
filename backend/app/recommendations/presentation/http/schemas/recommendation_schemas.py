"""Pydantic schemas for the recommendations endpoints."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.shared.presentation.i18n import LocalizedStr


class StartSessionRequest(BaseModel):
    ingredient_ids: list[str] = Field(
        default_factory=list,
        description="Ingredients to cook with (not stored in the pantry). Empty: use the pantry.",
    )
    min_score: float = Field(
        default=0.0, ge=0, le=1, description="Minimum share of a recipe's ingredients the user must have"
    )
    category_id: str | None = Field(default=None, description="Only recipes of this category (e.g. Cupcakes)")
    tag_ids: list[str] = Field(default_factory=list, max_length=10, description="Recipe must have all of these tags")


class NamedRefResponse(BaseModel):
    id: str
    name: LocalizedStr


class DiscoverySessionResponse(BaseModel):
    id: str
    ingredient_source: str  # 'selection' | 'pantry'
    ingredients: list[NamedRefResponse]
    category: NamedRefResponse | None
    tags: list[NamedRefResponse]
    min_score: float
    discarded_count: int
    saved_count: int
    selected_count: int
    created_at: datetime


class RecommendationResponse(BaseModel):
    recipe_id: str
    title: str
    description: str | None
    cover_photo_url: str | None
    category_name: LocalizedStr | None
    difficulty_name: LocalizedStr | None
    tags: list[LocalizedStr]
    prep_time_minutes: int | None
    servings: int | None
    is_own: bool = Field(description="The user's own recipe or personalization: already in their portfolio")
    is_personalization: bool
    source_recipe_title: str | None
    compatibility_score: float = Field(description="Share (0-1) of the recipe's ingredients the user has")
    equipment_score: float = Field(description="Share (0-1) of the recipe's equipment the user owns")
    rank_score: float = Field(description="Ordering score: 80% ingredients, 20% equipment")
    matched_ingredients: list[NamedRefResponse]
    missing_ingredients: list[NamedRefResponse]
    missing_equipment: list[NamedRefResponse]
    has_all_equipment: bool
    is_saved: bool


SwipeActionLiteral = Literal["discarded", "saved", "selected"]


class SwipeRequest(BaseModel):
    recipe_id: str
    action: SwipeActionLiteral


class SwipeResponse(BaseModel):
    id: str
    recipe_id: str
    action: str
    compatibility_score: float
    created_at: datetime
