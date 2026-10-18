"""
UnitSystemConverter — expresses a quantity in the user's preferred unit system.

Display only: the stored quantity of a recipe never changes. Rules, chosen
for how people actually measure when baking:

- To metric: weights become g (kg from 1000 g). US volumes become grams when
  the ingredient has a real weight for that measure (1 cup of flour = 125 g,
  which is how bakers weigh), otherwise ml (l from 1000 ml).
- To US: volumes become the most natural spoon/cup (cup from 1/4 cup, then
  tbsp, then tsp). Weights become cups/spoons when the ingredient has a
  volume<->weight figure (using the figure of that exact measure when it
  exists, since tbsp is not always cup/16), otherwise oz.
- Counted units ("unidad") and quantities already in the target system are
  left as they are.

Quantities are rounded the way a kitchen reads them: whole g/ml, quarters of
cups and spoons, one decimal for oz.

The measures of the ladder are identified by their seeded abbreviations
(cup, tbsp, tsp, g, kg, ml, l, oz).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.ingredients.domain.entities.unit import Unit, UnitSystem, UnitType
from app.ingredients.domain.value_objects.unit_id import UnitId

_QUARTER = Decimal("0.25")
# US volume ladder, biggest first, with the smallest amount worth expressing in each measure.
_US_VOLUME_LADDER = (("cup", Decimal("0.25")), ("tbsp", Decimal("1")), ("tsp", Decimal("0")))


@dataclass(frozen=True)
class DisplayQuantity:
    quantity: Decimal
    unit: Unit
    converted: bool


class UnitSystemConverter:
    def to_system(
        self,
        quantity: Decimal,
        unit: Unit,
        target: UnitSystem,
        units_by_abbreviation: dict[str, Unit],
        grams_per_unit: dict[UnitId, Decimal],
    ) -> DisplayQuantity:
        """`grams_per_unit`: this ingredient's weight for each volume measure that has a known figure."""
        if unit.unit_system in (target, UnitSystem.NEUTRAL) or unit.unit_type == UnitType.COUNT:
            return DisplayQuantity(_round(quantity, unit), unit, converted=False)

        units = units_by_abbreviation
        if target == UnitSystem.METRIC:
            if unit.unit_type == UnitType.WEIGHT:
                return self._metric(quantity * unit.base_factor, units["g"], units["kg"])
            if unit.id in grams_per_unit:
                return self._metric(quantity * grams_per_unit[unit.id], units["g"], units["kg"])
            return self._metric(quantity * unit.base_factor, units["ml"], units["l"])

        # target: US
        if unit.unit_type == UnitType.VOLUME:
            milliliters = quantity * unit.base_factor
            return self._us_ladder(lambda measure: milliliters / measure.base_factor, units)

        grams = quantity * unit.base_factor
        grams_per_ml = _grams_per_ml(grams_per_unit, units)
        if grams_per_ml is None:
            ounces = units["oz"]
            return DisplayQuantity(_round(grams / ounces.base_factor, ounces), ounces, converted=True)

        def amount_in(measure: Unit) -> Decimal:
            # Prefer the ingredient's own figure for this exact measure; derive it from volume otherwise.
            per_unit = grams_per_unit.get(measure.id) or grams_per_ml * measure.base_factor
            return grams / per_unit

        return self._us_ladder(amount_in, units)

    @staticmethod
    def _metric(base_amount: Decimal, base_unit: Unit, big_unit: Unit) -> DisplayQuantity:
        if base_amount >= big_unit.base_factor:
            return DisplayQuantity(_round(base_amount / big_unit.base_factor, big_unit), big_unit, converted=True)
        return DisplayQuantity(_round(base_amount, base_unit), base_unit, converted=True)

    @staticmethod
    def _us_ladder(amount_in, units: dict[str, Unit]) -> DisplayQuantity:
        for abbreviation, minimum in _US_VOLUME_LADDER:
            measure = units[abbreviation]
            amount = amount_in(measure)
            if amount >= minimum:
                rounded = _round(amount, measure)
                return DisplayQuantity(rounded if rounded > 0 else _QUARTER, measure, converted=True)
        raise AssertionError("unreachable: the last measure of the ladder accepts any amount")


def _grams_per_ml(grams_per_unit: dict[UnitId, Decimal], units: dict[str, Unit]) -> Decimal | None:
    for abbreviation, _ in _US_VOLUME_LADDER:
        measure = units[abbreviation]
        if measure.id in grams_per_unit:
            return grams_per_unit[measure.id] / measure.base_factor
    return None


def _round(quantity: Decimal, unit: Unit) -> Decimal:
    abbreviation = unit.abbreviation
    if abbreviation in ("g", "ml"):
        step = Decimal("0.1") if quantity < 10 else Decimal("1")
    elif abbreviation in ("cup", "tbsp", "tsp"):
        return (quantity / _QUARTER).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * _QUARTER
    elif abbreviation in ("kg", "l"):
        step = Decimal("0.01")
    elif abbreviation == "oz":
        step = Decimal("0.1")
    else:
        return quantity.normalize()
    return quantity.quantize(step, rounding=ROUND_HALF_UP)
