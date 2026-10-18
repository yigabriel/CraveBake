"""
MeasurementConverter — domain service that converts a quantity between
units, optionally using an ingredient-specific volume<->weight conversion.

Pure domain logic: given the involved Unit entities (and, when crossing
between volume and weight, an IngredientUnitConversion), it computes the
converted amount. It never talks to a repository — Application fetches the
entities and passes them in, which is what keeps this class trivially
testable without a database.
"""
from __future__ import annotations

from decimal import Decimal

from app.ingredients.domain.entities.ingredient_unit_conversion import IngredientUnitConversion
from app.ingredients.domain.entities.unit import Unit, UnitType
from app.ingredients.domain.exceptions import ConversionNotAvailableError


class MeasurementConverter:
    def convert(
        self,
        quantity: Decimal,
        from_unit: Unit,
        to_unit: Unit,
        ingredient_conversion: IngredientUnitConversion | None = None,
    ) -> Decimal:
        if from_unit.id == to_unit.id:
            return quantity

        if from_unit.unit_type == to_unit.unit_type:
            return self._convert_same_type(quantity, from_unit, to_unit)

        return self._convert_across_types(quantity, from_unit, to_unit, ingredient_conversion)

    def _convert_same_type(self, quantity: Decimal, from_unit: Unit, to_unit: Unit) -> Decimal:
        # base_factor = how many base units (g or ml) does 1 of this unit represent
        base_amount = quantity * from_unit.base_factor
        return base_amount / to_unit.base_factor

    def _convert_across_types(
        self,
        quantity: Decimal,
        from_unit: Unit,
        to_unit: Unit,
        ingredient_conversion: IngredientUnitConversion | None,
    ) -> Decimal:
        if from_unit.unit_type == UnitType.COUNT or to_unit.unit_type == UnitType.COUNT:
            raise ConversionNotAvailableError(from_unit.abbreviation, to_unit.abbreviation)

        if ingredient_conversion is None:
            raise ConversionNotAvailableError(from_unit.abbreviation, to_unit.abbreviation)

        volume_unit = from_unit if from_unit.unit_type == UnitType.VOLUME else to_unit
        # grams that 1 ml of this ingredient weighs, derived from "grams per 1 <volume_unit>"
        grams_per_ml = ingredient_conversion.grams_equivalent / volume_unit.base_factor

        if from_unit.unit_type == UnitType.VOLUME:
            grams = quantity * from_unit.base_factor * grams_per_ml
            return grams / to_unit.base_factor

        base_grams = quantity * from_unit.base_factor
        volume_in_ml = base_grams / grams_per_ml
        return volume_in_ml / to_unit.base_factor
