"""DTO for a unit of measurement."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class UnitDTO:
    id: str
    name: str
    abbreviation: str
    unit_type: str
    base_factor: Decimal
    unit_system: str  # metric | us | neutral
