"""
IngredientUnitConversion — the weight equivalent of one volume unit, for
one specific ingredient.

This is what lets the converter know that 1 cup of flour is ~120g while
1 cup of powdered sugar is ~130g, instead of assuming every ingredient
converts the same way.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.value_objects.ingredient_unit_conversion_id import (
    IngredientUnitConversionId,
)
from app.ingredients.domain.value_objects.unit_id import UnitId


@dataclass
class IngredientUnitConversion:
    id: IngredientUnitConversionId
    ingredient_id: IngredientId
    unit_id: UnitId  # must reference a volume unit
    grams_equivalent: Decimal
