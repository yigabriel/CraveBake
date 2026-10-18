"""
UpsertUserIngredientUseCase.

Registers or updates an ingredient in the user's permanent pantry
("ingredientes disponibles" in their profile). One user can only have one
pantry entry per ingredient — a second call with the same ingredient
updates the existing quantity/unit instead of creating a duplicate row.
"""
from __future__ import annotations

from decimal import Decimal

from app.ingredients.application.dto.ingredient_dto import IngredientDTO
from app.ingredients.application.dto.unit_dto import UnitDTO
from app.ingredients.application.dto.user_ingredient_dto import (
    UpsertUserIngredientDTO,
    UserIngredientDTO,
)
from app.ingredients.application.mappers.ingredient_mapper import ingredient_to_dto
from app.ingredients.application.mappers.unit_mapper import unit_to_dto
from app.ingredients.domain.entities.user_ingredient import UserIngredient
from app.ingredients.domain.exceptions import IngredientNotFoundError, UnitNotFoundError
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository
from app.ingredients.domain.repositories.unit_repository import UnitRepository
from app.ingredients.domain.repositories.user_ingredient_repository import UserIngredientRepository
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.value_objects.quantity import Quantity
from app.ingredients.domain.value_objects.unit_id import UnitId


class UpsertUserIngredientUseCase:
    def __init__(
        self,
        user_ingredient_repository: UserIngredientRepository,
        ingredient_repository: IngredientRepository,
        unit_repository: UnitRepository,
    ) -> None:
        self._user_ingredient_repository = user_ingredient_repository
        self._ingredient_repository = ingredient_repository
        self._unit_repository = unit_repository

    async def execute(self, dto: UpsertUserIngredientDTO) -> UserIngredientDTO:
        ingredient_id = IngredientId.from_string(dto.ingredient_id)
        ingredient = await self._ingredient_repository.get_by_id(ingredient_id)
        if ingredient is None:
            raise IngredientNotFoundError(dto.ingredient_id)

        unit = None
        if dto.unit_id is not None:
            unit = await self._unit_repository.get_by_id(UnitId.from_string(dto.unit_id))
            if unit is None:
                raise UnitNotFoundError(dto.unit_id)

        quantity: Decimal | None = None
        if dto.quantity is not None:
            quantity = Quantity(dto.quantity).value

        existing = await self._user_ingredient_repository.get_by_user_and_ingredient(
            dto.user_id, ingredient_id
        )

        if existing is not None:
            existing.update_quantity(quantity, unit.id if unit else None)
            await self._user_ingredient_repository.update(existing)
            user_ingredient = existing
        else:
            user_ingredient = UserIngredient.register(
                user_id=dto.user_id,
                ingredient_id=ingredient_id,
                quantity=quantity,
                unit_id=unit.id if unit else None,
            )
            await self._user_ingredient_repository.add(user_ingredient)

        return UserIngredientDTO(
            id=str(user_ingredient.id),
            ingredient=ingredient_to_dto(ingredient),
            quantity=user_ingredient.quantity,
            unit=unit_to_dto(unit) if unit else None,
            updated_at=user_ingredient.updated_at,
        )
