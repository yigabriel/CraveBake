"""
Equipment entity — a reusable catalog item (mold, utensil, appliance...).

Like an Ingredient, it belongs to the shared catalog, not to any user: the
same "Batidora planetaria" row is referenced by every recipe that needs it
and every kitchen that has one. Its name is a LocalizedText, written in its
creator's language; it must not clash with another item's name in any
language (enforced by the use case, via the repository, before construction).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from app.equipment.domain.value_objects.equipment_id import EquipmentId
from app.shared.domain.value_objects.localized_text import DEFAULT_LANGUAGE, LocalizedText


class EquipmentType(str, Enum):
    MOLD = "mold"
    UTENSIL = "utensil"
    APPLIANCE = "appliance"
    OTHER = "other"


@dataclass
class Equipment:
    id: EquipmentId
    name: LocalizedText
    equipment_type: EquipmentType
    description: str | None = None

    @classmethod
    def create(
        cls,
        name: str,
        equipment_type: EquipmentType,
        description: str | None = None,
        language: str = DEFAULT_LANGUAGE,
        translations: Mapping[str, str] | None = None,
    ) -> "Equipment":
        """`language`: the language `name` is written in (the creator's); `translations`: its other-language names."""
        return cls(
            id=EquipmentId(),
            name=LocalizedText.written(name, language, translations),
            equipment_type=equipment_type,
            description=(description or "").strip() or None,
        )

