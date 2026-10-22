"""
Anti-corruption layer: `ImportCatalog` on top of the public read APIs of the modules that own each
catalog (ingredients, equipment, recipes), translating their DTOs into this module's own types.
"""
from __future__ import annotations

from app.equipment.application.public.equipment_query_service import EquipmentQueryService
from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.recipe_import.domain.services.ports import (
    CatalogCategory,
    CatalogDifficulty,
    CatalogEquipment,
    CatalogIngredient,
    CatalogUnit,
    ImportCatalog,
)
from app.recipes.application.public.recipe_query_service import RecipeQueryService


class ModulesImportCatalog(ImportCatalog):
    def __init__(self, ingredients: IngredientQueryService, equipment: EquipmentQueryService, recipes: RecipeQueryService) -> None:
        self._ingredients = ingredients
        self._equipment = equipment
        self._recipes = recipes

    async def ingredients(self) -> list[CatalogIngredient]:
        return [CatalogIngredient(id=item.id, name=item.name) for item in await self._ingredients.list_catalog_ingredients()]

    async def units(self) -> list[CatalogUnit]:
        return [CatalogUnit(id=unit.id, name=unit.name, abbreviation=unit.abbreviation) for unit in await self._ingredients.list_units()]

    async def equipment(self) -> list[CatalogEquipment]:
        return [CatalogEquipment(id=item.id, name=item.name) for item in await self._equipment.list_catalog_equipment()]

    async def categories(self) -> list[CatalogCategory]:
        return [CatalogCategory(id=item.id, name=item.name) for item in await self._recipes.list_categories()]

    async def difficulties(self) -> list[CatalogDifficulty]:
        return [CatalogDifficulty(id=item.id, name=item.name, level_order=item.level_order) for item in await self._recipes.list_difficulties()]
