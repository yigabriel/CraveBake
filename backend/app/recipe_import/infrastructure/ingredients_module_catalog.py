"""
Anti-corruption layer: `ImportCatalog` on top of the ingredients module's public API
(`IngredientQueryService`), translating its DTOs into this module's own types.
"""
from __future__ import annotations

from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.recipe_import.domain.services.ports import CatalogIngredient, CatalogUnit, ImportCatalog


class IngredientsModuleCatalog(ImportCatalog):
    def __init__(self, ingredients: IngredientQueryService) -> None:
        self._ingredients = ingredients

    async def ingredients(self) -> list[CatalogIngredient]:
        return [CatalogIngredient(id=item.id, name=item.name) for item in await self._ingredients.list_catalog_ingredients()]

    async def units(self) -> list[CatalogUnit]:
        return [CatalogUnit(id=unit.id, name=unit.name, abbreviation=unit.abbreviation) for unit in await self._ingredients.list_units()]
