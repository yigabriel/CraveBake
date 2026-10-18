"""
ListMyRecipesUseCase — the recipes the current user created.

`kind` narrows the listing: 'original' (recipes they wrote from scratch),
'personalized' (their private variants of other recipes) or None for both.
"""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import RecipeSummaryDTO
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.domain.repositories.recipe_repository import RecipeRepository
from app.shared.application.pagination import Page

_PERSONALIZED_FILTER_BY_KIND: dict[str | None, bool | None] = {
    None: None,
    "original": False,
    "personalized": True,
}


class ListMyRecipesUseCase:
    def __init__(self, recipe_repository: RecipeRepository, assembler: RecipeAssembler) -> None:
        self._recipe_repository = recipe_repository
        self._assembler = assembler

    async def execute(
        self, user_id: str, kind: str | None = None, limit: int = 20, offset: int = 0
    ) -> Page[RecipeSummaryDTO]:
        page = await self._recipe_repository.list_by_owner(
            user_id, personalized=_PERSONALIZED_FILTER_BY_KIND[kind], limit=limit, offset=offset
        )
        return Page(
            items=await self._assembler.to_summaries(page.items, user_id),
            total=page.total,
            limit=limit,
            offset=offset,
        )
