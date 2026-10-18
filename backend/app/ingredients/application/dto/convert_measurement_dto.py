"""DTOs for the measurement converter."""
from dataclasses import dataclass
from decimal import Decimal

from app.ingredients.application.dto.unit_dto import UnitDTO


@dataclass(frozen=True)
class ConvertMeasurementDTO:
    quantity: Decimal
    from_unit_id: str
    to_unit_id: str
    ingredient_id: str | None = None


@dataclass(frozen=True)
class ConversionResultDTO:
    original_quantity: Decimal
    from_unit: UnitDTO
    to_unit: UnitDTO
    converted_quantity: Decimal
