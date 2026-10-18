"""
Equipment entity — a reusable catalog item (molde, utensilio, electrodoméstico...).

Like an Ingredient, it belongs to the shared catalog, not to any user: the
same "Batidora planetaria" row is referenced by every recipe that needs it
and every kitchen that has one. Name uniqueness is enforced by the use case
(via the repository) before this entity is constructed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.equipment.domain.value_objects.equipment_id import EquipmentId
from app.shared.exceptions.domain_exceptions import ValidationError


class EquipmentType(str, Enum):
    MOLDE = "molde"
    UTENSILIO = "utensilio"
    ELECTRODOMESTICO = "electrodomestico"
    OTRO = "otro"


@dataclass
class Equipment:
    id: EquipmentId
    name: str
    equipment_type: EquipmentType
    description: str | None = None

    @classmethod
    def create(cls, name: str, equipment_type: EquipmentType, description: str | None = None) -> "Equipment":
        return cls(
            id=EquipmentId(),
            name=_clean_name(name),
            equipment_type=equipment_type,
            description=(description or "").strip() or None,
        )


def _clean_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValidationError("Equipment name cannot be empty")
    return cleaned
