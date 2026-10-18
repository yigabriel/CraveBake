"""
Quantity value object.

Wraps a strictly positive decimal amount. Kept unit-agnostic on purpose —
the unit travels alongside it as a separate `UnitId` (see `UserIngredient`),
matching the data model's `quantity` + `unit_id` pair rather than bundling
both into one object.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.shared.exceptions.domain_exceptions import ValidationError


@dataclass(frozen=True)
class Quantity:
    value: Decimal

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValidationError("Quantity must be greater than zero")
