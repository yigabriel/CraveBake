"""DTOs for the equipment catalog and the user's kitchen."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from app.shared.domain.value_objects.localized_text import DEFAULT_LANGUAGE, LocalizedText


@dataclass(frozen=True)
class CreateEquipmentDTO:
    name: str
    equipment_type: str
    description: str | None = None
    language: str = DEFAULT_LANGUAGE  # the language `name` is written in
    # Reviewed translations of `name`, by language (the other languages' names).
    translations: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchEquipmentDTO:
    query: str | None = None
    equipment_type: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class EquipmentDTO:
    id: str
    name: LocalizedText  # every language; the HTTP layer picks the viewer's
    equipment_type: str
    description: str | None


@dataclass(frozen=True)
class UpsertUserEquipmentDTO:
    user_id: str
    equipment_id: str
    quantity: int = 1
    notes: str | None = None


@dataclass(frozen=True)
class UserEquipmentDTO:
    id: str
    equipment: EquipmentDTO
    quantity: int
    notes: str | None
    updated_at: datetime
