"""
RecipeRepository — port (interface) for the Recipe aggregate.

Persists and loads the whole aggregate (recipe + ingredients + steps +
photos) as one unit. Application depends only on this abstraction.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.recipes.domain.entities.recipe import Recipe
from app.recipes.domain.value_objects.difficulty_id import DifficultyId
from app.recipes.domain.value_objects.recipe_category_id import RecipeCategoryId
from app.recipes.domain.value_objects.recipe_id import RecipeId
from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId


@dataclass(frozen=True)
class RecipeSearchCriteria:
    """Filters for the public recipe search ("Explorar")."""

    query: str | None = None
    category_id: RecipeCategoryId | None = None
    difficulty_id: DifficultyId | None = None
    max_prep_time_minutes: int | None = None
    ingredient_ids: list[str] = field(default_factory=list)  # recipe must contain all of them
    tag_ids: list[RecipeTagId] = field(default_factory=list)  # recipe must have all of them
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class IngredientOverlapQuery:
    """Ranks the recipes a viewer can cook with some ingredients and equipment.

    Candidates: recipes visible to the viewer (public, or their own) that use
    at least one of `ingredient_ids`. Originals the viewer has personalized
    are replaced by their personalizations. Ordered by
    `ingredient_weight * ingredient_score + equipment_weight * equipment_score`,
    where the scores are the share of the recipe's ingredients / equipment
    the viewer has (equipment_score = 1 when the recipe lists none). The
    weights belong to whoever asks (recommendations), not to this module.
    """

    viewer_user_id: str
    ingredient_ids: list[str]
    equipment_ids: list[str]
    ingredient_weight: float
    equipment_weight: float
    min_ingredient_score: float = 0.0
    excluded_recipe_ids: list[RecipeId] = field(default_factory=list)
    category_id: RecipeCategoryId | None = None
    tag_ids: list[RecipeTagId] = field(default_factory=list)
    limit: int = 10
    offset: int = 0


@dataclass(frozen=True)
class RankedRecipeIds:
    recipe_ids: list[RecipeId]  # best first
    total: int  # candidates before pagination


@dataclass(frozen=True)
class RecipePage:
    items: list[Recipe]
    total: int  # matches before pagination


class RecipeRepository(ABC):
    @abstractmethod
    async def add(self, recipe: Recipe) -> None:
        ...

    @abstractmethod
    async def update(self, recipe: Recipe) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, recipe_id: RecipeId) -> Recipe | None:
        """Returns the recipe even if soft-deleted; callers decide visibility."""

    @abstractmethod
    async def get_many_by_ids(self, recipe_ids: list[RecipeId]) -> list[Recipe]:
        """Like `get_by_id`, in one batch. Unknown ids are omitted."""

    @abstractmethod
    async def rank_by_ingredient_overlap(self, query: IngredientOverlapQuery) -> RankedRecipeIds:
        """Scores, filters, orders and paginates in the database; see `IngredientOverlapQuery`."""

    @abstractmethod
    async def search_public(self, criteria: RecipeSearchCriteria) -> RecipePage:
        ...

    @abstractmethod
    async def list_by_owner(
        self,
        user_id: str,
        personalized: bool | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> RecipePage:
        """Non-deleted recipes created by the user, newest first.

        `personalized` filters originals/personalizations; `limit=None` returns them all.
        """

    @abstractmethod
    async def list_personalizations(
        self, source_recipe_id: RecipeId, user_id: str, limit: int | None = None, offset: int = 0
    ) -> RecipePage:
        """Non-deleted personalizations of `source_recipe_id` owned by `user_id`, newest first."""
