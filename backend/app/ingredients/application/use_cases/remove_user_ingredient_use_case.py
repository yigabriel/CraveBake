"""RemoveUserIngredientUseCase — removes an ingredient from the user's pantry."""
from __future__ import annotations

from app.ingredients.domain.repositories.user_ingredient_repository import UserIngredientRepository
from app.ingredients.domain.value_objects.ingredient_id import IngredientId


class RemoveUserIngredientUseCase:
    def __init__(self, user_ingredient_repository: UserIngredientRepository) -> None:
        self._user_ingredient_repository = user_ingredient_repository

    async def execute(self, user_id: str, ingredient_id: str) -> None:
        await self._user_ingredient_repository.remove(user_id, IngredientId.from_string(ingredient_id))
