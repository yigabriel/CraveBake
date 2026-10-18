"""SavedRecipeRepository — port (interface) for a user's favorites."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.portfolio.domain.entities.saved_recipe import SavedRecipe


class SavedRecipeRepository(ABC):
    @abstractmethod
    async def add(self, saved_recipe: SavedRecipe) -> None:
        ...

    @abstractmethod
    async def remove(self, user_id: str, recipe_id: str) -> None:
        ...

    @abstractmethod
    async def get(self, user_id: str, recipe_id: str) -> SavedRecipe | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[SavedRecipe]:
        ...

    @abstractmethod
    async def list_by_user_and_recipes(self, user_id: str, recipe_ids: list[str]) -> list[SavedRecipe]:
        ...
