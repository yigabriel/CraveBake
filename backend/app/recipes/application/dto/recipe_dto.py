"""DTOs for the recipes bounded context (inputs and outputs of its use cases)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

# --- Inputs ---------------------------------------------------------------------


@dataclass(frozen=True)
class RecipeIngredientInputDTO:
    ingredient_id: str
    quantity: Decimal
    unit_id: str
    notes: str | None = None


@dataclass(frozen=True)
class RecipeEquipmentInputDTO:
    equipment_id: str
    notes: str | None = None


@dataclass(frozen=True)
class RecipeStepInputDTO:
    instructions: str
    title: str | None = None
    timer_seconds: int | None = None
    id: str | None = None  # set to keep an existing step (and its photo) when replacing steps


@dataclass(frozen=True)
class CreateRecipeDTO:
    user_id: str
    title: str
    description: str | None = None
    video_url: str | None = None
    category_id: str | None = None
    difficulty_id: str | None = None
    prep_time_minutes: int | None = None
    servings: int | None = None
    is_public: bool = False
    ingredients: list[RecipeIngredientInputDTO] = field(default_factory=list)
    equipment: list[RecipeEquipmentInputDTO] = field(default_factory=list)
    tag_ids: list[str] = field(default_factory=list)
    steps: list[RecipeStepInputDTO] = field(default_factory=list)


@dataclass(frozen=True)
class UpdateRecipeDTO:
    """Partial update: only the keys present in `changes` are applied (an explicit None clears a field)."""

    user_id: str
    recipe_id: str
    changes: dict[str, Any]


@dataclass(frozen=True)
class SearchRecipesDTO:
    query: str | None = None
    category_id: str | None = None
    difficulty_id: str | None = None
    max_prep_time_minutes: int | None = None
    ingredient_ids: list[str] = field(default_factory=list)
    tag_ids: list[str] = field(default_factory=list)
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class AddRecipePhotoDTO:
    user_id: str
    recipe_id: str
    photo_type: str  # 'cover' | 'step'
    photo_url: str
    step_id: str | None = None


# --- Outputs --------------------------------------------------------------------


@dataclass(frozen=True)
class RecipeCategoryDTO:
    id: str
    name: str


@dataclass(frozen=True)
class DifficultyDTO:
    id: str
    name: str
    level_order: int


@dataclass(frozen=True)
class RecipeTagDTO:
    id: str
    name: str
    group: str  # stable code: sabor, dieta, tecnica, tiempo, celebraciones
    group_name: str  # display label


@dataclass(frozen=True)
class RecipeIngredientDTO:
    id: str
    ingredient_id: str
    ingredient_name: str | None
    quantity: Decimal
    unit_id: str
    unit_abbreviation: str | None
    notes: str | None
    position: int
    # How to show it in the requested unit system; equal to quantity/unit_abbreviation for 'original'.
    display_quantity: Decimal
    display_unit_abbreviation: str | None
    converted: bool


@dataclass(frozen=True)
class RecipeEquipmentDTO:
    id: str
    equipment_id: str
    equipment_name: str | None
    notes: str | None


@dataclass(frozen=True)
class RecipePhotoDTO:
    id: str
    photo_type: str
    photo_url: str
    position: int
    step_id: str | None


@dataclass(frozen=True)
class RecipeStepDTO:
    id: str
    step_number: int
    title: str | None
    instructions: str
    timer_seconds: int | None
    photo: RecipePhotoDTO | None


@dataclass(frozen=True)
class RecipeSummaryDTO:
    id: str
    title: str
    description: str | None
    cover_photo_url: str | None
    category: RecipeCategoryDTO | None
    difficulty: DifficultyDTO | None
    tags: list[RecipeTagDTO]
    prep_time_minutes: int | None
    servings: int | None
    is_public: bool
    is_personalization: bool
    source_recipe_id: str | None
    # Only for personalizations whose original is still visible to the viewer; None otherwise.
    source_recipe_title: str | None
    source_updated_since_personalized: bool | None
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RecipeDetailDTO:
    id: str
    title: str
    description: str | None
    video_url: str | None
    category: RecipeCategoryDTO | None
    difficulty: DifficultyDTO | None
    tags: list[RecipeTagDTO]
    prep_time_minutes: int | None
    servings: int | None
    is_public: bool
    is_personalization: bool
    source_recipe_id: str | None
    # Only for personalizations whose original is still visible to the viewer; None otherwise.
    source_recipe_title: str | None
    source_updated_since_personalized: bool | None
    created_by_user_id: str
    is_owner: bool
    cover_photos: list[RecipePhotoDTO]
    ingredients: list[RecipeIngredientDTO]
    equipment: list[RecipeEquipmentDTO]
    steps: list[RecipeStepDTO]
    created_at: datetime
    updated_at: datetime
    unit_system: str  # metric | us | original: the system the ingredients' display_* fields are in


@dataclass(frozen=True)
class RecipeCompositionDTO:
    """Published language for other contexts that need *what a recipe is made with*.

    Used by recommendations to score a recipe against the user's pantry and
    kitchen, without loading the full detail (steps, photos, names).
    """

    recipe: RecipeSummaryDTO
    ingredient_ids: list[str]
    equipment_ids: list[str]


@dataclass(frozen=True)
class IngredientOverlapQueryDTO:
    """Published-language input of `RecipeQueryService.rank_by_ingredient_overlap`."""

    viewer_user_id: str
    ingredient_ids: list[str]
    equipment_ids: list[str]
    ingredient_weight: float
    equipment_weight: float
    min_ingredient_score: float = 0.0
    excluded_recipe_ids: list[str] = field(default_factory=list)
    category_id: str | None = None
    tag_ids: list[str] = field(default_factory=list)
    limit: int = 10
    offset: int = 0


@dataclass(frozen=True)
class RankedRecipesDTO:
    recipe_ids: list[str]  # best first
    total: int
