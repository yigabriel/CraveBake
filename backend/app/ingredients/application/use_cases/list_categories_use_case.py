"""
ListCategoriesUseCase — every `default_category` code in use across the
ingredients catalog, with its display name and how many ingredients use it.
"""
from __future__ import annotations

from app.ingredients.application.dto.category_dto import CategoryDTO
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository


class ListCategoriesUseCase:
    def __init__(self, ingredient_repository: IngredientRepository) -> None:
        self._ingredient_repository = ingredient_repository

    async def execute(self) -> list[CategoryDTO]:
        rows = await self._ingredient_repository.list_distinct_categories()
        return [CategoryDTO(name=code, label=label, ingredient_count=count) for code, label, count in rows]
