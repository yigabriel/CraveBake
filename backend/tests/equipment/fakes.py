"""In-memory test doubles for the equipment ports."""
from __future__ import annotations

from app.equipment.domain.entities.equipment import Equipment, EquipmentType
from app.equipment.domain.entities.user_equipment import UserEquipment
from app.equipment.domain.repositories.equipment_repositories import (
    EquipmentRepository,
    UserEquipmentRepository,
)
from app.equipment.domain.value_objects.equipment_id import EquipmentId


class InMemoryEquipmentRepository(EquipmentRepository):

    def __init__(self) -> None:
        self.items: dict[EquipmentId, Equipment] = {}

    async def add(self, equipment: Equipment) -> None:
        self.items[equipment.id] = equipment

    async def get_by_id(self, equipment_id: EquipmentId) -> Equipment | None:
        return self.items.get(equipment_id)

    async def get_many_by_ids(self, ids: list[EquipmentId]) -> list[Equipment]:
        return [self.items[i] for i in ids if i in self.items]

    async def exists_by_name(self, name: str) -> bool:
        # Any language counts, like the real repository.
        return any(name.strip().lower() == text.lower() for item in self.items.values() for text in item.name.all_texts())

    def _matches(self, query: str | None, equipment_type: EquipmentType | None) -> list[Equipment]:
        return sorted(
            (
                item
                for item in self.items.values()
                if (not query or any(query.lower() in text.lower() for text in item.name.all_texts()))
                and (equipment_type is None or item.equipment_type is equipment_type)
            ),
            key=lambda item: item.name.text.lower(),
        )

    async def search(self, query, equipment_type, limit, offset) -> list[Equipment]:
        return self._matches(query, equipment_type)[offset : offset + limit]

    async def count(self, query, equipment_type) -> int:
        return len(self._matches(query, equipment_type))


class InMemoryUserEquipmentRepository(UserEquipmentRepository):

    def __init__(self) -> None:
        self.items: list[UserEquipment] = []

    async def add(self, user_equipment: UserEquipment) -> None:
        self.items.append(user_equipment)

    async def update(self, user_equipment: UserEquipment) -> None:
        pass  # entities are held by reference

    async def remove(self, user_id: str, equipment_id: EquipmentId) -> None:
        self.items = [
            i for i in self.items if not (i.user_id == user_id and i.equipment_id == equipment_id)
        ]

    async def get_by_user_and_equipment(self, user_id, equipment_id) -> UserEquipment | None:
        return next(
            (i for i in self.items if i.user_id == user_id and i.equipment_id == equipment_id), None
        )

    async def list_by_user(self, user_id: str) -> list[UserEquipment]:
        return [i for i in self.items if i.user_id == user_id]
