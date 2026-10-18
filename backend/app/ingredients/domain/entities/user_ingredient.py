"""
UserIngredient — one item in a user's permanent pantry.

This is the "ingredientes disponibles" a user registers on their profile —
independent from the temporary ingredient selection used in "¿Qué quiero
cocinar?", which is never persisted here.

`user_id` is kept as an opaque string (a UUID minted by the IAM bounded
context), not as IAM's `UserId` value object: bounded contexts reference
each other by id only, never by importing one another's domain types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.value_objects.unit_id import UnitId
from app.ingredients.domain.value_objects.user_ingredient_id import UserIngredientId


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserIngredient:
    id: UserIngredientId
    user_id: str
    ingredient_id: IngredientId
    quantity: Decimal | None = None
    unit_id: UnitId | None = None
    updated_at: datetime = field(default_factory=_utc_now)

    @classmethod
    def register(
        cls,
        user_id: str,
        ingredient_id: IngredientId,
        quantity: Decimal | None = None,
        unit_id: UnitId | None = None,
    ) -> "UserIngredient":
        return cls(id=UserIngredientId(), user_id=user_id, ingredient_id=ingredient_id, quantity=quantity, unit_id=unit_id)

    def update_quantity(self, quantity: Decimal | None, unit_id: UnitId | None) -> None:
        self.quantity = quantity
        self.unit_id = unit_id
        self.updated_at = _utc_now()
