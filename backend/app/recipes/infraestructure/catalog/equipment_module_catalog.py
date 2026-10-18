"""
Anti-corruption layer towards the equipment bounded context.

Implements the recipes-side `EquipmentCatalog` port on top of the equipment
module's public API (`EquipmentQueryService`). Recipes never touches the
equipment tables.
"""
from __future__ import annotations

from app.equipment.application.public.equipment_query_service import EquipmentQueryService
from app.recipes.domain.services.equipment_catalog import CatalogEquipment, EquipmentCatalog


class EquipmentModuleCatalog(EquipmentCatalog):
    def __init__(self, equipment: EquipmentQueryService) -> None:
        self._equipment = equipment

    async def get_equipment(self, ids: list[str]) -> dict[str, CatalogEquipment]:
        return {
            item.id: CatalogEquipment(id=item.id, name=item.name)
            for item in await self._equipment.get_equipment(ids)
        }
