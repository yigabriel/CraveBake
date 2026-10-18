"""
Anti-corruption layer towards the ingredients bounded context.

Implements the recipes-side `IngredientCatalog` port on top of the
ingredients module's public API (`IngredientQueryService`), translating its
DTOs into the minimal shapes recipes needs. Recipes never touches the
ingredients tables: if their schema changes, only the ingredients module
has to adapt, as long as its public contract holds.
"""
from __future__ import annotations

from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.recipes.domain.services.ingredient_catalog import CatalogIngredient, CatalogUnit, IngredientCatalog


class IngredientsModuleCatalog(IngredientCatalog):
    def __init__(self, ingredients: IngredientQueryService) -> None:
        self._ingredients = ingredients

    async def get_ingredients(self, ids: list[str]) -> dict[str, CatalogIngredient]:
        return {
            item.id: CatalogIngredient(id=item.id, name=item.name)
            for item in await self._ingredients.get_ingredients(ids)
        }

    async def get_units(self, ids: list[str]) -> dict[str, CatalogUnit]:
        return {
            unit.id: CatalogUnit(id=unit.id, name=unit.name, abbreviation=unit.abbreviation)
            for unit in await self._ingredients.get_units(ids)
        }
