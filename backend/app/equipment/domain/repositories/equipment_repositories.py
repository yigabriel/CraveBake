"""Ports (interfaces) for the equipment catalog and the user's kitchen."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.equipment.domain.entities.equipment import Equipment, EquipmentType
from app.equipment.domain.entities.user_equipment import UserEquipment
from app.equipment.domain.value_objects.equipment_id import EquipmentId


class EquipmentRepository(ABC):
    @abstractmethod
    async def add(self, equipment: Equipment) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, equipment_id: EquipmentId) -> Equipment | None:
        ...

    @abstractmethod
    async def get_many_by_ids(self, ids: list[EquipmentId]) -> list[Equipment]:
        ...

    @abstractmethod
    async def exists_by_name(self, name: str) -> bool:
        ...

    @abstractmethod
    async def search(
        self, query: str | None, equipment_type: EquipmentType | None, limit: int, offset: int
    ) -> list[Equipment]:
        ...

    @abstractmethod
    async def count(self, query: str | None, equipment_type: EquipmentType | None) -> int:
        """Total matches of `search` with the same filters, ignoring pagination."""


class UserEquipmentRepository(ABC):
    @abstractmethod
    async def add(self, user_equipment: UserEquipment) -> None:
        ...

    @abstractmethod
    async def update(self, user_equipment: UserEquipment) -> None:
        ...

    @abstractmethod
    async def remove(self, user_id: str, equipment_id: EquipmentId) -> None:
        ...

    @abstractmethod
    async def get_by_user_and_equipment(self, user_id: str, equipment_id: EquipmentId) -> UserEquipment | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[UserEquipment]:
        ...
