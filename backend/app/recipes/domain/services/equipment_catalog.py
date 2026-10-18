"""
EquipmentCatalog — port towards the equipment bounded context.

Recipes reference equipment by opaque ids. This port is how the recipes
module checks those ids exist and fetches their display names, without
importing anything from the equipment module's domain.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogEquipment:
    id: str
    name: str


class EquipmentCatalog(ABC):
    @abstractmethod
    async def get_equipment(self, ids: list[str]) -> dict[str, CatalogEquipment]:
        """Returns the equipment that exists, keyed by id. Unknown ids are omitted."""
