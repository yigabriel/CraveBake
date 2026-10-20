"""
CreateRecipeUseCase.

Creates an original recipe owned by the current user, with its ingredient
lines and steps in one go. Every referenced id (category, difficulty,
ingredients, units) is validated first. Photos are added afterwards through
the photo endpoints, since step photos need the ids of the created steps.
"""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import CreateRecipeDTO, RecipeDetailDTO
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.application.services.recipe_reference_validator import RecipeReferenceValidator
from app.recipes.domain.entities.recipe import Recipe, StepDraft
from app.recipes.domain.repositories.recipe_repository import RecipeRepository


class CreateRecipeUseCase:
    def __init__(
        self,
        recipe_repository: RecipeRepository,
        reference_validator: RecipeReferenceValidator,
        assembler: RecipeAssembler,
    ) -> None:
        self._recipe_repository = recipe_repository
        self._reference_validator = reference_validator
        self._assembler = assembler

    async def execute(self, dto: CreateRecipeDTO) -> RecipeDetailDTO:
        recipe = Recipe.create(
            created_by_user_id=dto.user_id,
            title=dto.title,
            description=dto.description,
            video_url=dto.video_url,
            category_id=await self._reference_validator.category(dto.category_id),
            difficulty_id=await self._reference_validator.difficulty(dto.difficulty_id),
            prep_time_minutes=dto.prep_time_minutes,
            servings=dto.servings,
            is_public=dto.is_public,
            ingredients=await self._reference_validator.ingredient_lines(dto.ingredients),
            equipment=await self._reference_validator.equipment_lines(dto.equipment),
            tag_ids=await self._reference_validator.tags(dto.tag_ids),
            steps=[
                StepDraft(
                    instructions=step.instructions,
                    title=step.title,
                    timer_seconds=step.timer_seconds,
                    section=step.section,
                )
                for step in dto.steps
            ],
        )
        await self._recipe_repository.add(recipe)
        return await self._assembler.to_detail(recipe, dto.user_id)
