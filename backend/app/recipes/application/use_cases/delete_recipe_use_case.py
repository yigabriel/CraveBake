"""
DeleteRecipeUseCase — logical deletion (owner only).

Sets `deleted_at` instead of removing the row: favorites, personalizations
and preparation sessions may still reference it. Personalizations of a
deleted original keep working, since they are full independent copies.
"""
from __future__ import annotations

from app.recipes.application.services.recipe_access import load_owned_recipe
from app.recipes.domain.repositories.recipe_repository import RecipeRepository


class DeleteRecipeUseCase:
    def __init__(self, recipe_repository: RecipeRepository) -> None:
        self._recipe_repository = recipe_repository

    async def execute(self, user_id: str, recipe_id: str) -> None:
        recipe = await load_owned_recipe(self._recipe_repository, recipe_id, user_id)
        recipe.soft_delete()
        await self._recipe_repository.update(recipe)
