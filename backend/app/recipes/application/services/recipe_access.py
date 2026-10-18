"""
Shared access checks used by the recipe use cases.

- Reading: a recipe that is deleted, or private and owned by someone else,
  is reported as "not found" (404), never as "forbidden", so its existence
  is not revealed.
- Writing: additionally requires ownership. A visible-but-foreign recipe
  (a public one by another user) gives 403.
"""
from __future__ import annotations

from app.recipes.domain.entities.recipe import Recipe
from app.recipes.domain.exceptions import RecipeAccessDeniedError, RecipeNotFoundError
from app.recipes.domain.repositories.recipe_repository import RecipeRepository
from app.recipes.domain.value_objects.recipe_id import RecipeId


async def load_visible_recipe(repository: RecipeRepository, recipe_id: str, user_id: str) -> Recipe:
    parsed_id = RecipeId.try_from_string(recipe_id)
    recipe = await repository.get_by_id(parsed_id) if parsed_id else None
    if recipe is None or not recipe.is_visible_to(user_id):
        raise RecipeNotFoundError(recipe_id)
    return recipe


async def load_owned_recipe(repository: RecipeRepository, recipe_id: str, user_id: str) -> Recipe:
    recipe = await load_visible_recipe(repository, recipe_id, user_id)
    if not recipe.is_owned_by(user_id):
        raise RecipeAccessDeniedError(recipe_id)
    return recipe
