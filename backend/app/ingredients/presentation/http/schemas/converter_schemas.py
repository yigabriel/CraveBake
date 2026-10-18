"""Pydantic schemas for the measurement converter endpoint."""
from decimal import Decimal

from pydantic import BaseModel, Field

from app.ingredients.presentation.http.schemas.unit_schemas import UnitResponse


class ConvertMeasurementRequest(BaseModel):
    quantity: Decimal = Field(gt=0)
    from_unit_id: str
    to_unit_id: str
    ingredient_id: str | None = None


class ConvertMeasurementResponse(BaseModel):
    original_quantity: Decimal
    from_unit: UnitResponse
    to_unit: UnitResponse
    converted_quantity: Decimal
