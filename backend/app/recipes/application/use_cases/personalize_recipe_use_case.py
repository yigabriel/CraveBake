"""
PersonalizeRecipeUseCase — "adapto la receta a mi horno / a mi país, solo para mí".

Any recipe the user can see (a public one, or one of their own originals)
can be personalized, as many times as they want. The result is a new,
always-private recipe linked through `source_recipe_id`; the original is
never modified. A personalization cannot be personalized again.
"""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import RecipeDetailDTO
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.application.services.recipe_access import load_visible_recipe
from app.recipes.domain.repositories.recipe_repository import RecipeRepository


class PersonalizeRecipeUseCase:
    def __init__(self, recipe_repository: RecipeRepository, assembler: RecipeAssembler) -> None:
        self._recipe_repository = recipe_repository
        self._assembler = assembler

    async def execute(self, user_id: str, recipe_id: str, title: str | None = None) -> RecipeDetailDTO:
        source = await load_visible_recipe(self._recipe_repository, recipe_id, user_id)
        personalization = source.personalize(user_id, title=title)
        await self._recipe_repository.add(personalization)
        return await self._assembler.to_detail(personalization, user_id)
