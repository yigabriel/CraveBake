"""DTOs of the "show this quantity in my unit system" capability (public API)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class QuantityToDisplayDTO:
    ingredient_id: str
    quantity: Decimal
    unit_id: str


@dataclass(frozen=True)
class DisplayQuantityDTO:
    quantity: Decimal
    unit_id: str
    unit_abbreviation: str
    converted: bool  # False when it was already in the requested system (or cannot be converted)
