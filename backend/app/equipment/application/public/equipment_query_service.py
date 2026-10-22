"""
EquipmentQueryService — the equipment module's public read API (Open Host Service).

The only entry point other bounded contexts may use to read equipment:
recipes (to validate and name the equipment a recipe needs) and
recommendations (to know what the user owns). They receive this module's
DTOs and translate them in their own anti-corruption layer.
"""
from __future__ import annotations

from app.equipment.application.dto.equipment_dto import EquipmentDTO
from app.equipment.application.mappers.equipment_mapper import equipment_to_dto
from app.equipment.domain.repositories.equipment_repositories import (
    EquipmentRepository,
    UserEquipmentRepository,
)
from app.equipment.domain.value_objects.equipment_id import EquipmentId


class EquipmentQueryService:
    def __init__(
        self, equipment_repository: EquipmentRepository, user_equipment_repository: UserEquipmentRepository
    ) -> None:
        self._equipment_repository = equipment_repository
        self._user_equipment_repository = user_equipment_repository

    async def get_equipment(self, ids: list[str]) -> list[EquipmentDTO]:
        """Equipment that exists among `ids`; unknown or malformed ids are skipped."""
        parsed = list({parsed for raw in ids if (parsed := EquipmentId.try_from_string(raw)) is not None})
        return [equipment_to_dto(item) for item in await self._equipment_repository.get_many_by_ids(parsed)]

    async def list_catalog_equipment(self, limit: int = 200) -> list[EquipmentDTO]:
        """The shared equipment catalog, in name order (capped: callers match free text against it)."""
        return [equipment_to_dto(item) for item in await self._equipment_repository.search(None, None, limit, 0)]

    async def list_user_equipment_ids(self, user_id: str) -> list[str]:
        """Ids of the equipment the user has in their kitchen."""
        return [str(item.equipment_id) for item in await self._user_equipment_repository.list_by_user(user_id)]
