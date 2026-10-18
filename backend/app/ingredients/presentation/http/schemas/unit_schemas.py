"""Pydantic schema for a measurement unit."""
from decimal import Decimal

from pydantic import BaseModel


class UnitResponse(BaseModel):
    id: str
    name: str
    abbreviation: str
    unit_type: str
    base_factor: Decimal
    unit_system: str  # metric | us | neutral
