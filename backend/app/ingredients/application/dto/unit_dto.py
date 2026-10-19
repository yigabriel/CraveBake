"""DTO for a unit of measurement."""
from dataclasses import dataclass
from decimal import Decimal
from app.shared.domain.value_objects.localized_text import LocalizedText


@dataclass(frozen=True)
class UnitDTO:
    id: str
    name: LocalizedText
    abbreviation: str
    unit_type: str
    base_factor: Decimal
    unit_system: str  # metric | us | neutral
