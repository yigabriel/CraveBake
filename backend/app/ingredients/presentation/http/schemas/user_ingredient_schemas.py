"""Pydantic schemas for the user's pantry endpoints."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.ingredients.presentation.http.schemas.ingredient_schemas import IngredientResponse
from app.ingredients.presentation.http.schemas.unit_schemas import UnitResponse


class UpsertUserIngredientRequest(BaseModel):
    ingredient_id: str
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_id: str | None = None


class UserIngredientResponse(BaseModel):
    id: str
    ingredient: IngredientResponse
    quantity: Decimal | None
    unit: UnitResponse | None
    updated_at: datetime
