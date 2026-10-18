"""
ListCategoriesUseCase — returns every distinct `default_category` currently
in use across the ingredients catalog, with how many ingredients use each.

Categories are free text (see `IngredientRepository.list_distinct_categories`
docstring for why), so this reflects whatever values `POST /ingredients`
has been given so far rather than a fixed, curated list.
"""
from __future__ import annotations

from app.ingredients.application.dto.category_dto import CategoryDTO
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository


class ListCategoriesUseCase:
    def __init__(self, ingredient_repository: IngredientRepository) -> None:
        self._ingredient_repository = ingredient_repository

    async def execute(self) -> list[CategoryDTO]:
        rows = await self._ingredient_repository.list_distinct_categories()
        return [CategoryDTO(name=name, ingredient_count=count) for name, count in rows]
