"""ReplaceRecipeEquipmentUseCase — replaces the equipment list a recipe needs (owner only)."""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import RecipeDetailDTO, RecipeEquipmentInputDTO
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.application.services.recipe_access import load_owned_recipe
from app.recipes.application.services.recipe_reference_validator import RecipeReferenceValidator
from app.recipes.domain.repositories.recipe_repository import RecipeRepository


class ReplaceRecipeEquipmentUseCase:
    def __init__(
        self,
        recipe_repository: RecipeRepository,
        reference_validator: RecipeReferenceValidator,
        assembler: RecipeAssembler,
    ) -> None:
        self._recipe_repository = recipe_repository
        self._reference_validator = reference_validator
        self._assembler = assembler

    async def execute(
        self, user_id: str, recipe_id: str, equipment: list[RecipeEquipmentInputDTO]
    ) -> RecipeDetailDTO:
        recipe = await load_owned_recipe(self._recipe_repository, recipe_id, user_id)
        recipe.replace_equipment(await self._reference_validator.equipment_lines(equipment))
        await self._recipe_repository.update(recipe)
        return await self._assembler.to_detail(recipe, user_id)
