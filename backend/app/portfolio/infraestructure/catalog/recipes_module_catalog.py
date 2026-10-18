"""
Anti-corruption layer towards the recipes bounded context.

Implements portfolio's `RecipeCatalog` port on top of the recipes module's
public API (`RecipeQueryService`), translating its published language
(`RecipeSummaryDTO`) into portfolio's own `RecipeSnapshot`. Portfolio never
touches the recipes tables and never re-implements the visibility rule:
if recipes changes how it stores or hides recipes, nothing here changes as
long as the public contract holds.
"""
from __future__ import annotations

from app.portfolio.domain.services.recipe_catalog import RecipeCatalog, RecipeSnapshot
from app.recipes.application.dto.recipe_dto import RecipeSummaryDTO
from app.recipes.application.public.recipe_query_service import RecipeQueryService


class RecipesModuleCatalog(RecipeCatalog):
    def __init__(self, recipes: RecipeQueryService) -> None:
        self._recipes = recipes

    async def get_visible(self, recipe_id: str, viewer_user_id: str) -> RecipeSnapshot | None:
        summary = await self._recipes.get_visible(recipe_id, viewer_user_id)
        return _to_snapshot(summary) if summary else None

    async def get_many_visible(self, recipe_ids: list[str], viewer_user_id: str) -> dict[str, RecipeSnapshot]:
        summaries = await self._recipes.get_many_visible(recipe_ids, viewer_user_id)
        return {summary.id: _to_snapshot(summary) for summary in summaries}

    async def list_owned_by(self, user_id: str) -> list[RecipeSnapshot]:
        return [_to_snapshot(summary) for summary in await self._recipes.list_owned_by(user_id)]


def _to_snapshot(summary: RecipeSummaryDTO) -> RecipeSnapshot:
    return RecipeSnapshot(
        id=summary.id,
        title=summary.title,
        description=summary.description,
        cover_photo_url=summary.cover_photo_url,
        category_id=summary.category.id if summary.category else None,
        category_name=summary.category.name if summary.category else None,
        tag_ids=frozenset(tag.id for tag in summary.tags),
        tag_names=tuple(tag.name for tag in summary.tags),
        difficulty_name=summary.difficulty.name if summary.difficulty else None,
        prep_time_minutes=summary.prep_time_minutes,
        servings=summary.servings,
        is_public=summary.is_public,
        created_by_user_id=summary.created_by_user_id,
        source_recipe_id=summary.source_recipe_id,
        source_recipe_title=summary.source_recipe_title,
        source_updated_since_personalized=summary.source_updated_since_personalized,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
    )
