"""SearchIngredientsUseCase — powers the ingredient picker used across Explorar and "¿Qué quiero cocinar?"."""
from __future__ import annotations

from app.ingredients.application.dto.ingredient_dto import IngredientDTO, SearchIngredientsDTO
from app.ingredients.application.mappers.ingredient_mapper import ingredient_to_dto
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository
from app.shared.application.pagination import Page


class SearchIngredientsUseCase:
    def __init__(self, ingredient_repository: IngredientRepository) -> None:
        self._ingredient_repository = ingredient_repository

    async def execute(self, dto: SearchIngredientsDTO) -> Page[IngredientDTO]:
        ingredients = await self._ingredient_repository.search(
            query=dto.query, category=dto.category, limit=dto.limit, offset=dto.offset
        )
        total = await self._ingredient_repository.count(query=dto.query, category=dto.category)
        return Page(
            items=[ingredient_to_dto(ingredient) for ingredient in ingredients],
            total=total,
            limit=dto.limit,
            offset=dto.offset,
        )
