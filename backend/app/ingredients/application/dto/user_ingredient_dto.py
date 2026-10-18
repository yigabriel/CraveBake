"""DTOs for a user's pantry."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.ingredients.application.dto.ingredient_dto import IngredientDTO
from app.ingredients.application.dto.unit_dto import UnitDTO


@dataclass(frozen=True)
class UpsertUserIngredientDTO:
    user_id: str
    ingredient_id: str
    quantity: Decimal | None = None
    unit_id: str | None = None


@dataclass(frozen=True)
class UserIngredientDTO:
    id: str
    ingredient: IngredientDTO
    quantity: Decimal | None
    unit: UnitDTO | None
    updated_at: datetime
