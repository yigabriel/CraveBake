"""Ports (interfaces) for the read-only recipe catalogs: categories, difficulties and tags."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.recipes.domain.entities.difficulty import Difficulty
from app.recipes.domain.entities.recipe_category import RecipeCategory
from app.recipes.domain.entities.recipe_tag import RecipeTag
from app.recipes.domain.value_objects.difficulty_id import DifficultyId
from app.recipes.domain.value_objects.recipe_category_id import RecipeCategoryId
from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId


class RecipeCategoryRepository(ABC):
    @abstractmethod
    async def get_by_id(self, category_id: RecipeCategoryId) -> RecipeCategory | None:
        ...

    @abstractmethod
    async def list_all(self) -> list[RecipeCategory]:
        ...


class DifficultyRepository(ABC):
    @abstractmethod
    async def get_by_id(self, difficulty_id: DifficultyId) -> Difficulty | None:
        ...

    @abstractmethod
    async def list_all(self) -> list[Difficulty]:
        ...


class RecipeTagRepository(ABC):
    @abstractmethod
    async def get_many_by_ids(self, tag_ids: list[RecipeTagId]) -> list[RecipeTag]:
        ...

    @abstractmethod
    async def list_all(self) -> list[RecipeTag]:
        ...
