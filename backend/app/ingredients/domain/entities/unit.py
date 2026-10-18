"""
Unit entity — a catalog unit of measurement.

`unit_type` groups units that can be converted between each other with a
plain factor (weight<->weight, volume<->volume). Converting *across* types
(volume<->weight) additionally needs an `IngredientUnitConversion`, since
that ratio depends on the ingredient (flour vs. powdered sugar).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from app.ingredients.domain.value_objects.unit_id import UnitId


class UnitType(str, Enum):
    WEIGHT = "weight"
    VOLUME = "volume"
    COUNT = "count"


class UnitSystem(str, Enum):
    """Which measuring tradition a unit belongs to (users pick one in their profile)."""

    METRIC = "metric"  # g, kg, ml, l
    US = "us"  # cup, tbsp, tsp, oz
    NEUTRAL = "neutral"  # counted units, valid in both


@dataclass
class Unit:
    id: UnitId
    name: str
    abbreviation: str
    unit_type: UnitType
    base_factor: Decimal  # how many base units (g for weight, ml for volume) one of this unit represents
    unit_system: UnitSystem = UnitSystem.NEUTRAL
