"""
ReplaceRecipeStepsUseCase — replaces the step list of a recipe (owner only).

Steps are renumbered in the order given. Sending a step with its existing
`id` keeps it (and its photo); steps left out are deleted with their photo.
"""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import RecipeDetailDTO, RecipeStepInputDTO
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.application.services.recipe_access import load_owned_recipe
from app.recipes.domain.entities.recipe import StepDraft
from app.recipes.domain.exceptions import RecipeStepNotFoundError
from app.recipes.domain.repositories.recipe_repository import RecipeRepository
from app.recipes.domain.value_objects.recipe_step_id import RecipeStepId


class ReplaceRecipeStepsUseCase:
    def __init__(self, recipe_repository: RecipeRepository, assembler: RecipeAssembler) -> None:
        self._recipe_repository = recipe_repository
        self._assembler = assembler

    async def execute(self, user_id: str, recipe_id: str, steps: list[RecipeStepInputDTO]) -> RecipeDetailDTO:
        recipe = await load_owned_recipe(self._recipe_repository, recipe_id, user_id)
        recipe.replace_steps([_to_draft(step) for step in steps])
        await self._recipe_repository.update(recipe)
        return await self._assembler.to_detail(recipe, user_id)


def _to_draft(step: RecipeStepInputDTO) -> StepDraft:
    step_id = None
    if step.id is not None:
        step_id = RecipeStepId.try_from_string(step.id)
        if step_id is None:
            raise RecipeStepNotFoundError(step.id)
    return StepDraft(
        instructions=step.instructions, title=step.title, timer_seconds=step.timer_seconds, id=step_id
    )
