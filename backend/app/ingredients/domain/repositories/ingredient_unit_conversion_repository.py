"""IngredientUnitConversionRepository — port (interface) for per-ingredient volume<->weight ratios."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.ingredients.domain.entities.ingredient_unit_conversion import IngredientUnitConversion
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.value_objects.unit_id import UnitId


class IngredientUnitConversionRepository(ABC):
    @abstractmethod
    async def add(self, conversion: IngredientUnitConversion) -> None:
        ...

    @abstractmethod
    async def get_by_ingredient_and_unit(
        self, ingredient_id: IngredientId, unit_id: UnitId
    ) -> IngredientUnitConversion | None:
        ...

    @abstractmethod
    async def list_by_ingredients(self, ingredient_ids: list[IngredientId]) -> list[IngredientUnitConversion]:
        ...
