"""Pydantic schemas for the recipes endpoints."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.shared.presentation.i18n import LocalizedStr

# --- Requests -----------------------------------------------------------------------


class RecipeIngredientRequest(BaseModel):
    ingredient_id: str
    quantity: Decimal = Field(gt=0)
    unit_id: str
    notes: str | None = Field(default=None, max_length=500)
    section: str | None = Field(
        default=None,
        max_length=100,
        description="Name of the group it belongs to (\"Masa choux\"). Lines without a group go first, then each group's lines together",
    )


class RecipeEquipmentRequest(BaseModel):
    equipment_id: str
    notes: str | None = Field(default=None, max_length=500)


class RecipeStepRequest(BaseModel):
    instructions: str = Field(min_length=1)
    title: str | None = Field(default=None, max_length=200)
    timer_seconds: int | None = Field(default=None, gt=0)
    id: str | None = Field(default=None, description="Existing step id, to keep it (and its photo) when replacing steps")
    section: str | None = Field(
        default=None,
        max_length=100,
        description="Name of the group it belongs to (\"Masa choux\"). Steps without a group go first, then each group's steps together",
    )


class CreateRecipeRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    video_url: str | None = Field(default=None, max_length=1024)
    category_id: str | None = None
    difficulty_id: str | None = None
    prep_time_minutes: int | None = Field(default=None, gt=0)
    servings: int | None = Field(default=None, gt=0)
    is_public: bool = False
    ingredients: list[RecipeIngredientRequest] = Field(default_factory=list)
    equipment: list[RecipeEquipmentRequest] = Field(default_factory=list)
    tag_ids: list[str] = Field(default_factory=list, max_length=10)
    steps: list[RecipeStepRequest] = Field(default_factory=list)


class UpdateRecipeRequest(BaseModel):
    """Partial update: omit a field to keep it, send null to clear it (title and is_public cannot be null)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    video_url: str | None = Field(default=None, max_length=1024)
    category_id: str | None = None
    difficulty_id: str | None = None
    prep_time_minutes: int | None = Field(default=None, gt=0)
    servings: int | None = Field(default=None, gt=0)
    is_public: bool | None = None


class ReplaceIngredientsRequest(BaseModel):
    ingredients: list[RecipeIngredientRequest]


class ReplaceEquipmentRequest(BaseModel):
    equipment: list[RecipeEquipmentRequest]


class ReplaceTagsRequest(BaseModel):
    tag_ids: list[str] = Field(max_length=10)


class ReplaceStepsRequest(BaseModel):
    steps: list[RecipeStepRequest]


class PersonalizeRecipeRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class AddRecipePhotoRequest(BaseModel):
    photo_type: Literal["cover", "step"]
    photo_url: str = Field(min_length=1, max_length=1024)
    step_id: str | None = None


class ReorderCoverPhotosRequest(BaseModel):
    photo_ids: list[str]


# --- Responses ----------------------------------------------------------------------


class RecipeCategoryResponse(BaseModel):
    id: str
    name: LocalizedStr


class DifficultyResponse(BaseModel):
    id: str
    name: LocalizedStr
    level_order: int


class RecipeTagResponse(BaseModel):
    id: str
    name: LocalizedStr
    group: str  # sabor | dieta | tecnica | tiempo | celebraciones
    group_name: LocalizedStr


class RecipePhotoResponse(BaseModel):
    id: str
    photo_type: str
    photo_url: str
    position: int
    step_id: str | None


class RecipeIngredientResponse(BaseModel):
    id: str
    ingredient_id: str
    ingredient_name: LocalizedStr | None
    quantity: Decimal
    unit_id: str
    unit_abbreviation: str | None
    notes: str | None
    position: int
    section_id: str | None
    section: str | None = Field(description="Name of the group the line belongs to; null when it has none")
    display_quantity: Decimal = Field(description="Quantity in the response's unit_system (as written for 'original')")
    display_unit_abbreviation: str | None
    converted: bool = Field(description="True if display_* differ from the quantity/unit the author wrote")


class RecipeEquipmentResponse(BaseModel):
    id: str
    equipment_id: str
    equipment_name: LocalizedStr | None
    notes: str | None


class RecipeStepResponse(BaseModel):
    id: str
    step_number: int
    title: str | None
    instructions: str
    timer_seconds: int | None
    photo: RecipePhotoResponse | None
    section_id: str | None
    section: str | None = Field(description="Name of the group the step belongs to; null when it has none")


class RecipeSummaryResponse(BaseModel):
    id: str
    title: str
    description: str | None
    cover_photo_url: str | None
    category: RecipeCategoryResponse | None
    difficulty: DifficultyResponse | None
    tags: list[RecipeTagResponse]
    prep_time_minutes: int | None
    servings: int | None
    is_public: bool
    is_personalization: bool
    source_recipe_id: str | None
    source_recipe_title: str | None = Field(
        description="Title of the original; null if not a personalization or the original is no longer visible"
    )
    source_updated_since_personalized: bool | None = Field(
        description="True if the original changed after this personalization was made; null when not applicable"
    )
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class RecipeDetailResponse(BaseModel):
    id: str
    title: str
    description: str | None
    video_url: str | None
    category: RecipeCategoryResponse | None
    difficulty: DifficultyResponse | None
    tags: list[RecipeTagResponse]
    prep_time_minutes: int | None
    servings: int | None
    is_public: bool
    is_personalization: bool
    source_recipe_id: str | None
    source_recipe_title: str | None = Field(
        description="Title of the original; null if not a personalization or the original is no longer visible"
    )
    source_updated_since_personalized: bool | None = Field(
        description="True if the original changed after this personalization was made; null when not applicable"
    )
    created_by_user_id: str
    is_owner: bool
    cover_photos: list[RecipePhotoResponse]
    ingredients: list[RecipeIngredientResponse]
    equipment: list[RecipeEquipmentResponse]
    steps: list[RecipeStepResponse]
    created_at: datetime
    updated_at: datetime
    unit_system: str = Field(description="metric | us | original: the system of the ingredients' display_* fields")
