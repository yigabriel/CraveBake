"""Pydantic schema for a measurement unit."""
from decimal import Decimal

from pydantic import BaseModel
from app.shared.presentation.i18n import LocalizedStr


class UnitResponse(BaseModel):
    id: str
    name: LocalizedStr
    abbreviation: str
    unit_type: str
    base_factor: Decimal
    unit_system: str  # metric | us | neutral
