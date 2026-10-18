"""
PortfolioReader — loads everything that makes up a user's portfolio.

Shared by the listing and summary use cases. Portfolios are small (one
user's recipes and favorites), so they are assembled in memory and then
filtered and paginated, instead of building one cross-table SQL query.
"""
from __future__ import annotations

from app.portfolio.application.dto.portfolio_dto import PortfolioItemDTO
from app.portfolio.domain.entities.portfolio_entry import PortfolioEntry, build_portfolio
from app.portfolio.domain.repositories.saved_recipe_repository import SavedRecipeRepository
from app.portfolio.domain.services.recipe_catalog import RecipeCatalog


class PortfolioReader:
    def __init__(self, saved_recipe_repository: SavedRecipeRepository, recipe_catalog: RecipeCatalog) -> None:
        self._saved_recipe_repository = saved_recipe_repository
        self._recipe_catalog = recipe_catalog

    async def load(self, user_id: str) -> list[PortfolioEntry]:
        owned = await self._recipe_catalog.list_owned_by(user_id)
        saved = await self._saved_recipe_repository.list_by_user(user_id)
        visible_saved = await self._recipe_catalog.get_many_visible([entry.recipe_id for entry in saved], user_id)
        return build_portfolio(user_id, owned, saved, visible_saved)


def entry_to_dto(entry: PortfolioEntry) -> PortfolioItemDTO:
    recipe = entry.recipe
    return PortfolioItemDTO(
        kind=entry.kind.value,
        recipe_id=recipe.id,
        title=recipe.title,
        description=recipe.description,
        cover_photo_url=recipe.cover_photo_url,
        category_name=recipe.category_name,
        tags=list(recipe.tag_names),
        difficulty_name=recipe.difficulty_name,
        prep_time_minutes=recipe.prep_time_minutes,
        servings=recipe.servings,
        is_public=recipe.is_public,
        created_by_user_id=recipe.created_by_user_id,
        source_recipe_id=recipe.source_recipe_id,
        source_recipe_title=recipe.source_recipe_title,
        source_updated_since_personalized=recipe.source_updated_since_personalized,
        added_at=entry.added_at,
    )
