"""
FavoritesService — the portfolio module's public API (Open Host Service).

Lets other bounded contexts (recommendations' "save" swipe) add favorites
and check which recipes are saved, without knowing how favorites are
stored. Saving reuses `SaveRecipeUseCase`, so every rule (only visible
recipes, never your own, idempotent) applies no matter who calls it.
"""
from __future__ import annotations

from app.portfolio.application.use_cases.favorite_use_cases import SaveRecipeUseCase
from app.portfolio.domain.repositories.saved_recipe_repository import SavedRecipeRepository


class FavoritesService:
    def __init__(self, save_recipe_use_case: SaveRecipeUseCase, saved_recipe_repository: SavedRecipeRepository) -> None:
        self._save_recipe_use_case = save_recipe_use_case
        self._saved_recipe_repository = saved_recipe_repository

    async def save(self, user_id: str, recipe_id: str) -> None:
        """Adds the recipe to the user's favorites (no-op if already saved)."""
        await self._save_recipe_use_case.execute(user_id, recipe_id)

    async def saved_among(self, user_id: str, recipe_ids: list[str]) -> set[str]:
        """The subset of `recipe_ids` the user has saved."""
        saved = await self._saved_recipe_repository.list_by_user_and_recipes(user_id, recipe_ids)
        return {entry.recipe_id for entry in saved}
