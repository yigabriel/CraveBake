"""ListUnitsUseCase — returns the full reference catalog of measurement units."""
from __future__ import annotations

from app.ingredients.application.dto.unit_dto import UnitDTO
from app.ingredients.application.mappers.unit_mapper import unit_to_dto
from app.ingredients.domain.repositories.unit_repository import UnitRepository


class ListUnitsUseCase:
    def __init__(self, unit_repository: UnitRepository) -> None:
        self._unit_repository = unit_repository

    async def execute(self) -> list[UnitDTO]:
        units = await self._unit_repository.list_all()
        return [unit_to_dto(unit) for unit in units]
