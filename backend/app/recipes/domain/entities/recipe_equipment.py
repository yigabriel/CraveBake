"""
RecipeEquipment — one item of equipment a recipe needs (e.g. "Molde de 24 cm").

`equipment_id` is an opaque string minted by the equipment bounded context:
recipes never import equipment's domain types.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.recipes.domain.value_objects.recipe_equipment_id import RecipeEquipmentId


@dataclass
class RecipeEquipment:
    id: RecipeEquipmentId
    equipment_id: str
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.notes is not None:
            self.notes = self.notes.strip() or None
