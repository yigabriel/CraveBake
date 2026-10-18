"""
CreateIngredientUseCase.

Adds a new item to the shared ingredients catalog. Any authenticated user
can contribute new ingredients (there is no admin role yet), but uniqueness
of the name is enforced so recipes and pantries always reference the same
underlying `Ingredient` row instead of accumulating near-duplicates.
"""
from __future__ import annotations

from app.ingredients.application.dto.ingredient_dto import CreateIngredientDTO, IngredientDTO
from app.ingredients.application.mappers.ingredient_mapper import ingredient_to_dto
from app.ingredients.domain.entities.ingredient import Ingredient
from app.ingredients.domain.exceptions import IngredientAlreadyExistsError
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository


class CreateIngredientUseCase:
    def __init__(self, ingredient_repository: IngredientRepository) -> None:
        self._ingredient_repository = ingredient_repository

    async def execute(self, dto: CreateIngredientDTO) -> IngredientDTO:
        if await self._ingredient_repository.exists_by_name(dto.name.strip()):
            raise IngredientAlreadyExistsError(dto.name)

        ingredient = Ingredient.create(
            name=dto.name, description=dto.description, default_category=dto.default_category
        )
        await self._ingredient_repository.add(ingredient)

        return ingredient_to_dto(ingredient)
