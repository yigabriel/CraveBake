"""
Equipment catalog use cases: search, detail and creation.

Any authenticated user can add equipment (there is no admin role yet, same
as ingredients); names are unique, case-insensitively, so recipes and
kitchens always point to the same row instead of near-duplicates.
"""
from __future__ import annotations

from app.equipment.application.dto.equipment_dto import CreateEquipmentDTO, EquipmentDTO, SearchEquipmentDTO
from app.equipment.application.mappers.equipment_mapper import equipment_to_dto
from app.equipment.domain.entities.equipment import Equipment, EquipmentType
from app.equipment.domain.exceptions import EquipmentAlreadyExistsError, EquipmentNotFoundError
from app.equipment.domain.repositories.equipment_repositories import EquipmentRepository
from app.equipment.domain.value_objects.equipment_id import EquipmentId
from app.shared.application.pagination import Page


class SearchEquipmentUseCase:
    def __init__(self, equipment_repository: EquipmentRepository) -> None:
        self._equipment_repository = equipment_repository

    async def execute(self, dto: SearchEquipmentDTO) -> Page[EquipmentDTO]:
        equipment_type = EquipmentType(dto.equipment_type) if dto.equipment_type else None
        items = await self._equipment_repository.search(dto.query, equipment_type, dto.limit, dto.offset)
        total = await self._equipment_repository.count(dto.query, equipment_type)
        return Page(items=[equipment_to_dto(item) for item in items], total=total, limit=dto.limit, offset=dto.offset)


class GetEquipmentUseCase:
    def __init__(self, equipment_repository: EquipmentRepository) -> None:
        self._equipment_repository = equipment_repository

    async def execute(self, equipment_id: str) -> EquipmentDTO:
        parsed_id = EquipmentId.try_from_string(equipment_id)
        equipment = await self._equipment_repository.get_by_id(parsed_id) if parsed_id else None
        if equipment is None:
            raise EquipmentNotFoundError(equipment_id)
        return equipment_to_dto(equipment)


class CreateEquipmentUseCase:
    def __init__(self, equipment_repository: EquipmentRepository) -> None:
        self._equipment_repository = equipment_repository

    async def execute(self, dto: CreateEquipmentDTO) -> EquipmentDTO:
        if await self._equipment_repository.exists_by_name(dto.name.strip()):
            raise EquipmentAlreadyExistsError(dto.name)
        equipment = Equipment.create(
            name=dto.name, equipment_type=EquipmentType(dto.equipment_type), description=dto.description, language=dto.language
        )
        await self._equipment_repository.add(equipment)
        return equipment_to_dto(equipment)
