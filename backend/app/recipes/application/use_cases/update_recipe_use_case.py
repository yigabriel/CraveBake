"""
UpdateRecipeUseCase — partial update of a recipe's general data (owner only).

Only the fields present in `dto.changes` are touched. Ingredients, steps and
photos have their own use cases, since they are lists with their own rules.
"""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import RecipeDetailDTO, UpdateRecipeDTO
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.application.services.recipe_access import load_owned_recipe
from app.recipes.application.services.recipe_reference_validator import RecipeReferenceValidator
from app.recipes.domain.repositories.recipe_repository import RecipeRepository

_UPDATABLE_FIELDS = {
    "title",
    "description",
    "video_url",
    "category_id",
    "difficulty_id",
    "prep_time_minutes",
    "servings",
    "is_public",
}


class UpdateRecipeUseCase:
    def __init__(
        self,
        recipe_repository: RecipeRepository,
        reference_validator: RecipeReferenceValidator,
        assembler: RecipeAssembler,
    ) -> None:
        self._recipe_repository = recipe_repository
        self._reference_validator = reference_validator
        self._assembler = assembler

    async def execute(self, dto: UpdateRecipeDTO) -> RecipeDetailDTO:
        recipe = await load_owned_recipe(self._recipe_repository, dto.recipe_id, dto.user_id)

        changes = {key: value for key, value in dto.changes.items() if key in _UPDATABLE_FIELDS}
        if "category_id" in changes:
            changes["category_id"] = await self._reference_validator.category(changes["category_id"])
        if "difficulty_id" in changes:
            changes["difficulty_id"] = await self._reference_validator.difficulty(changes["difficulty_id"])

        recipe.update_details(**changes)
        await self._recipe_repository.update(recipe)
        return await self._assembler.to_detail(recipe, dto.user_id)
