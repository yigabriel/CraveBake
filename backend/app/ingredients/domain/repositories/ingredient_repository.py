"""
IngredientRepository — port (interface) for the ingredients catalog.

Application depends only on this abstraction; Infrastructure provides the
SQLAlchemy implementation. Domain never imports SQLAlchemy.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.ingredients.domain.entities.ingredient import Ingredient
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.shared.domain.value_objects.localized_text import LocalizedText


class IngredientRepository(ABC):
    @abstractmethod
    async def add(self, ingredient: Ingredient) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, ingredient_id: IngredientId) -> Ingredient | None:
        ...

    @abstractmethod
    async def get_many_by_ids(self, ids: list[IngredientId]) -> list[Ingredient]:
        ...

    @abstractmethod
    async def exists_by_name(self, name: str) -> bool:
        """True if any ingredient is called `name` in any language, ignoring case."""

    @abstractmethod
    async def search(  # `query` matches the name in any language
        self, query: str | None, category: str | None, limit: int, offset: int
    ) -> list[Ingredient]:
        ...

    @abstractmethod
    async def count(self, query: str | None, category: str | None) -> int:
        """Total matches of `search` with the same filters, ignoring pagination."""

    @abstractmethod
    async def list_distinct_categories(self) -> list[tuple[str, LocalizedText, int]]:
        """Each `default_category` code in use, its display name, and how many ingredients have it.

        Codes are set when an ingredient is created; the seeded ones have a
        localized name, any other code is named as written.
        """
