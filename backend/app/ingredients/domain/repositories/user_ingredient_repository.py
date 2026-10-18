"""UserIngredientRepository — port (interface) for a user's pantry entries."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.ingredients.domain.entities.user_ingredient import UserIngredient
from app.ingredients.domain.value_objects.ingredient_id import IngredientId


class UserIngredientRepository(ABC):
    @abstractmethod
    async def add(self, user_ingredient: UserIngredient) -> None:
        ...

    @abstractmethod
    async def update(self, user_ingredient: UserIngredient) -> None:
        ...

    @abstractmethod
    async def remove(self, user_id: str, ingredient_id: IngredientId) -> None:
        ...

    @abstractmethod
    async def get_by_user_and_ingredient(
        self, user_id: str, ingredient_id: IngredientId
    ) -> UserIngredient | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[UserIngredient]:
        ...
