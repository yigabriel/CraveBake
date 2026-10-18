"""
ListUserIngredientsUseCase — returns everything the user has registered in
their pantry, enriched with ingredient and unit display data.

Note: enriches each pantry row with individual repository calls, which is a
readable, N+1-shaped approach acceptable for the small pantry sizes this
feature expects. A batch fetch (`IngredientRepository.get_many_by_ids`) is
already available on the repository interface if this needs optimizing.
"""
from __future__ import annotations

from app.ingredients.application.dto.user_ingredient_dto import UserIngredientDTO
from app.ingredients.application.mappers.ingredient_mapper import ingredient_to_dto
from app.ingredients.application.mappers.unit_mapper import unit_to_dto
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository
from app.ingredients.domain.repositories.unit_repository import UnitRepository
from app.ingredients.domain.repositories.user_ingredient_repository import UserIngredientRepository


class ListUserIngredientsUseCase:
    def __init__(
        self,
        user_ingredient_repository: UserIngredientRepository,
        ingredient_repository: IngredientRepository,
        unit_repository: UnitRepository,
    ) -> None:
        self._user_ingredient_repository = user_ingredient_repository
        self._ingredient_repository = ingredient_repository
        self._unit_repository = unit_repository

    async def execute(self, user_id: str) -> list[UserIngredientDTO]:
        pantry_items = await self._user_ingredient_repository.list_by_user(user_id)

        ingredients_by_id = {
            ingredient.id: ingredient
            for ingredient in await self._ingredient_repository.get_many_by_ids(
                [item.ingredient_id for item in pantry_items]
            )
        }

        result: list[UserIngredientDTO] = []
        for item in pantry_items:
            ingredient = ingredients_by_id.get(item.ingredient_id)
            if ingredient is None:
                continue  # defensive: skip orphaned rows rather than failing the whole listing
            unit = await self._unit_repository.get_by_id(item.unit_id) if item.unit_id else None
            result.append(
                UserIngredientDTO(
                    id=str(item.id),
                    ingredient=ingredient_to_dto(ingredient),
                    quantity=item.quantity,
                    unit=unit_to_dto(unit) if unit else None,
                    updated_at=item.updated_at,
                )
            )
        return result
