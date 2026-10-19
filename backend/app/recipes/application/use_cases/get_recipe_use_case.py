"""GetRecipeUseCase — full detail of a recipe visible to the user (public, or their own)."""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import RecipeDetailDTO
from app.recipes.application.mappers.recipe_assembler import ORIGINAL_UNITS, RecipeAssembler
from app.recipes.application.services.recipe_access import load_visible_recipe
from app.recipes.domain.repositories.recipe_repository import RecipeRepository


class GetRecipeUseCase:
    def __init__(self, recipe_repository: RecipeRepository, assembler: RecipeAssembler) -> None:
        self._recipe_repository = recipe_repository
        self._assembler = assembler

    async def execute(self, recipe_id: str, user_id: str, unit_system: str = ORIGINAL_UNITS) -> RecipeDetailDTO:
        """`unit_system` ('metric' | 'us' | 'original') is how the ingredient quantities are displayed."""
        recipe = await load_visible_recipe(self._recipe_repository, recipe_id, user_id)
        return await self._assembler.to_detail(recipe, user_id, unit_system)
