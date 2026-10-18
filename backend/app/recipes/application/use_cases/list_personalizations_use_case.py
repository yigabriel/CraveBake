"""ListPersonalizationsUseCase — the current user's own variants of one recipe."""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import RecipeSummaryDTO
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.application.services.recipe_access import load_visible_recipe
from app.recipes.domain.repositories.recipe_repository import RecipeRepository
from app.shared.application.pagination import Page


class ListPersonalizationsUseCase:
    def __init__(self, recipe_repository: RecipeRepository, assembler: RecipeAssembler) -> None:
        self._recipe_repository = recipe_repository
        self._assembler = assembler

    async def execute(
        self, user_id: str, recipe_id: str, limit: int = 20, offset: int = 0
    ) -> Page[RecipeSummaryDTO]:
        source = await load_visible_recipe(self._recipe_repository, recipe_id, user_id)
        page = await self._recipe_repository.list_personalizations(source.id, user_id, limit=limit, offset=offset)
        return Page(
            items=await self._assembler.to_summaries(page.items, user_id),
            total=page.total,
            limit=limit,
            offset=offset,
        )
