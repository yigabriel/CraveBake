"""UnitRepository — port (interface) for the units reference catalog."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.ingredients.domain.entities.unit import Unit
from app.ingredients.domain.value_objects.unit_id import UnitId


class UnitRepository(ABC):
    @abstractmethod
    async def get_by_id(self, unit_id: UnitId) -> Unit | None:
        ...

    @abstractmethod
    async def get_many_by_ids(self, ids: list[UnitId]) -> list[Unit]:
        ...

    @abstractmethod
    async def list_all(self) -> list[Unit]:
        ...
