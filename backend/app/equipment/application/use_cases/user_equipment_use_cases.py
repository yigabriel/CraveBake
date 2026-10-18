"""
The user's kitchen: which equipment they own.

One entry per equipment item: registering the same item again updates its
quantity and notes instead of creating a duplicate (same as the pantry).
"""
from __future__ import annotations

from app.equipment.application.dto.equipment_dto import UpsertUserEquipmentDTO, UserEquipmentDTO
from app.equipment.application.mappers.equipment_mapper import user_equipment_to_dto
from app.equipment.domain.entities.user_equipment import UserEquipment
from app.equipment.domain.exceptions import EquipmentNotFoundError
from app.equipment.domain.repositories.equipment_repositories import (
    EquipmentRepository,
    UserEquipmentRepository,
)
from app.equipment.domain.value_objects.equipment_id import EquipmentId


class ListUserEquipmentUseCase:
    def __init__(
        self, user_equipment_repository: UserEquipmentRepository, equipment_repository: EquipmentRepository
    ) -> None:
        self._user_equipment_repository = user_equipment_repository
        self._equipment_repository = equipment_repository

    async def execute(self, user_id: str) -> list[UserEquipmentDTO]:
        items = await self._user_equipment_repository.list_by_user(user_id)
        catalog = {
            equipment.id: equipment
            for equipment in await self._equipment_repository.get_many_by_ids([item.equipment_id for item in items])
        }
        return [
            user_equipment_to_dto(item, catalog[item.equipment_id])
            for item in items
            if item.equipment_id in catalog  # defensive: skip orphaned rows rather than failing the listing
        ]


class UpsertUserEquipmentUseCase:
    def __init__(
        self, user_equipment_repository: UserEquipmentRepository, equipment_repository: EquipmentRepository
    ) -> None:
        self._user_equipment_repository = user_equipment_repository
        self._equipment_repository = equipment_repository

    async def execute(self, dto: UpsertUserEquipmentDTO) -> UserEquipmentDTO:
        equipment_id = EquipmentId.try_from_string(dto.equipment_id)
        equipment = await self._equipment_repository.get_by_id(equipment_id) if equipment_id else None
        if equipment is None:
            raise EquipmentNotFoundError(dto.equipment_id)

        item = await self._user_equipment_repository.get_by_user_and_equipment(dto.user_id, equipment.id)
        if item is not None:
            item.update(dto.quantity, dto.notes)
            await self._user_equipment_repository.update(item)
        else:
            item = UserEquipment.register(dto.user_id, equipment.id, dto.quantity, dto.notes)
            await self._user_equipment_repository.add(item)

        return user_equipment_to_dto(item, equipment)


class RemoveUserEquipmentUseCase:
    def __init__(self, user_equipment_repository: UserEquipmentRepository) -> None:
        self._user_equipment_repository = user_equipment_repository

    async def execute(self, user_id: str, equipment_id: str) -> None:
        parsed_id = EquipmentId.try_from_string(equipment_id)
        if parsed_id is not None:
            await self._user_equipment_repository.remove(user_id, parsed_id)
