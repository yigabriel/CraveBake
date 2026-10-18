"""DTOs for the equipment catalog and the user's kitchen."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CreateEquipmentDTO:
    name: str
    equipment_type: str
    description: str | None = None


@dataclass(frozen=True)
class SearchEquipmentDTO:
    query: str | None = None
    equipment_type: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class EquipmentDTO:
    id: str
    name: str
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
