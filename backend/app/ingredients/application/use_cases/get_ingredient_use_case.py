"""GetIngredientUseCase — fetch a single catalog ingredient by id."""
from __future__ import annotations

from app.ingredients.application.dto.ingredient_dto import IngredientDTO
from app.ingredients.application.mappers.ingredient_mapper import ingredient_to_dto
from app.ingredients.domain.exceptions import IngredientNotFoundError
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository
from app.ingredients.domain.value_objects.ingredient_id import IngredientId


class GetIngredientUseCase:
    def __init__(self, ingredient_repository: IngredientRepository) -> None:
        self._ingredient_repository = ingredient_repository

    async def execute(self, ingredient_id: str) -> IngredientDTO:
        parsed_id = IngredientId.try_from_string(ingredient_id)
        ingredient = await self._ingredient_repository.get_by_id(parsed_id) if parsed_id else None
        if ingredient is None:
            raise IngredientNotFoundError(ingredient_id)
        return ingredient_to_dto(ingredient)
