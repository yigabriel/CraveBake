"""
Favorites use cases: save, unsave, and check saved status.

Saving and unsaving are idempotent, so the client can map them directly to
a heart toggle: saving twice returns the existing favorite, and unsaving a
recipe that is not saved is a no-op.
"""
from __future__ import annotations

from app.portfolio.application.dto.portfolio_dto import FavoriteStatusDTO, PortfolioItemDTO
from app.portfolio.application.use_cases.portfolio_reader import entry_to_dto
from app.portfolio.domain.entities.portfolio_entry import PortfolioEntry, PortfolioItemKind
from app.portfolio.domain.entities.saved_recipe import SavedRecipe
from app.portfolio.domain.exceptions import PortfolioRecipeNotFoundError
from app.portfolio.domain.repositories.saved_recipe_repository import SavedRecipeRepository
from app.portfolio.domain.services.recipe_catalog import RecipeCatalog


class SaveRecipeUseCase:
    def __init__(self, saved_recipe_repository: SavedRecipeRepository, recipe_catalog: RecipeCatalog) -> None:
        self._saved_recipe_repository = saved_recipe_repository
        self._recipe_catalog = recipe_catalog

    async def execute(self, user_id: str, recipe_id: str) -> PortfolioItemDTO:
        recipe = await self._recipe_catalog.get_visible(recipe_id, user_id)
        if recipe is None:
            raise PortfolioRecipeNotFoundError(recipe_id)

        saved = await self._saved_recipe_repository.get(user_id, recipe.id)
        if saved is None:
            saved = SavedRecipe.save(user_id, recipe)
            await self._saved_recipe_repository.add(saved)

        return entry_to_dto(PortfolioEntry(kind=PortfolioItemKind.SAVED, recipe=recipe, added_at=saved.saved_at))


class UnsaveRecipeUseCase:
    def __init__(self, saved_recipe_repository: SavedRecipeRepository) -> None:
        self._saved_recipe_repository = saved_recipe_repository

    async def execute(self, user_id: str, recipe_id: str) -> None:
        await self._saved_recipe_repository.remove(user_id, recipe_id)


class GetFavoriteStatusUseCase:
    """Saved status of several recipes at once, e.g. to paint the hearts of a results page."""

    def __init__(self, saved_recipe_repository: SavedRecipeRepository) -> None:
        self._saved_recipe_repository = saved_recipe_repository

    async def execute(self, user_id: str, recipe_ids: list[str]) -> list[FavoriteStatusDTO]:
        saved = {
            entry.recipe_id: entry
            for entry in await self._saved_recipe_repository.list_by_user_and_recipes(user_id, recipe_ids)
        }
        return [
            FavoriteStatusDTO(
                recipe_id=recipe_id,
                is_saved=recipe_id in saved,
                saved_at=saved[recipe_id].saved_at if recipe_id in saved else None,
            )
            for recipe_id in dict.fromkeys(recipe_ids)  # de-duplicated, order preserved
        ]
