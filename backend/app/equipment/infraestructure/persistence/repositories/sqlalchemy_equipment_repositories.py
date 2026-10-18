"""SQLAlchemy implementations of `EquipmentRepository` and `UserEquipmentRepository`."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.equipment.domain.entities.equipment import Equipment, EquipmentType
from app.equipment.domain.entities.user_equipment import UserEquipment
from app.equipment.domain.repositories.equipment_repositories import (
    EquipmentRepository,
    UserEquipmentRepository,
)
from app.equipment.domain.value_objects.equipment_id import EquipmentId
from app.equipment.domain.value_objects.user_equipment_id import UserEquipmentId
from app.equipment.infraestructure.persistence.models.equipment_model import EquipmentModel
from app.equipment.infraestructure.persistence.models.user_equipment_model import UserEquipmentModel


class SqlAlchemyEquipmentRepository(EquipmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, equipment: Equipment) -> None:
        self._session.add(
            EquipmentModel(
                id=equipment.id.value,
                name=equipment.name,
                equipment_type=equipment.equipment_type.value,
                description=equipment.description,
            )
        )
        await self._session.flush()

    async def get_by_id(self, equipment_id: EquipmentId) -> Equipment | None:
        model = await self._session.get(EquipmentModel, equipment_id.value)
        return _to_equipment(model) if model else None

    async def get_many_by_ids(self, ids: list[EquipmentId]) -> list[Equipment]:
        if not ids:
            return []
        result = await self._session.execute(
            select(EquipmentModel).where(EquipmentModel.id.in_([equipment_id.value for equipment_id in ids]))
        )
        return [_to_equipment(model) for model in result.scalars().all()]

    async def exists_by_name(self, name: str) -> bool:
        result = await self._session.execute(
            select(EquipmentModel.id).where(func.lower(EquipmentModel.name) == name.lower())
        )
        return result.scalar_one_or_none() is not None

    async def search(
        self, query: str | None, equipment_type: EquipmentType | None, limit: int, offset: int
    ) -> list[Equipment]:
        statement = _filtered(select(EquipmentModel), query, equipment_type)
        statement = statement.order_by(EquipmentModel.name).limit(limit).offset(offset)
        result = await self._session.execute(statement)
        return [_to_equipment(model) for model in result.scalars().all()]

    async def count(self, query: str | None, equipment_type: EquipmentType | None) -> int:
        statement = _filtered(select(func.count()).select_from(EquipmentModel), query, equipment_type)
        return (await self._session.execute(statement)).scalar_one()


class SqlAlchemyUserEquipmentRepository(UserEquipmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_equipment: UserEquipment) -> None:
        self._session.add(
            UserEquipmentModel(
                id=user_equipment.id.value,
                user_id=uuid.UUID(user_equipment.user_id),
                equipment_id=user_equipment.equipment_id.value,
                quantity=user_equipment.quantity,
                notes=user_equipment.notes,
            )
        )
        await self._session.flush()

    async def update(self, user_equipment: UserEquipment) -> None:
        model = await self._session.get(UserEquipmentModel, user_equipment.id.value)
        if model is None:
            return
        model.quantity = user_equipment.quantity
        model.notes = user_equipment.notes
        await self._session.flush()

    async def remove(self, user_id: str, equipment_id: EquipmentId) -> None:
        await self._session.execute(
            delete(UserEquipmentModel).where(
                UserEquipmentModel.user_id == uuid.UUID(user_id),
                UserEquipmentModel.equipment_id == equipment_id.value,
            )
        )
        await self._session.flush()

    async def get_by_user_and_equipment(self, user_id: str, equipment_id: EquipmentId) -> UserEquipment | None:
        result = await self._session.execute(
            select(UserEquipmentModel).where(
                UserEquipmentModel.user_id == uuid.UUID(user_id),
                UserEquipmentModel.equipment_id == equipment_id.value,
            )
        )
        model = result.scalar_one_or_none()
        return _to_user_equipment(model) if model else None

    async def list_by_user(self, user_id: str) -> list[UserEquipment]:
        result = await self._session.execute(
            select(UserEquipmentModel)
            .where(UserEquipmentModel.user_id == uuid.UUID(user_id))
            .order_by(UserEquipmentModel.created_at)
        )
        return [_to_user_equipment(model) for model in result.scalars().all()]


def _filtered(statement, query: str | None, equipment_type: EquipmentType | None):
    if query:
        statement = statement.where(EquipmentModel.name.ilike(f"%{query}%"))
    if equipment_type:
        statement = statement.where(EquipmentModel.equipment_type == equipment_type.value)
    return statement


def _to_equipment(model: EquipmentModel) -> Equipment:
    return Equipment(
        id=EquipmentId(model.id),
        name=model.name,
        equipment_type=EquipmentType(model.equipment_type),
        description=model.description,
    )


def _to_user_equipment(model: UserEquipmentModel) -> UserEquipment:
    return UserEquipment(
        id=UserEquipmentId(model.id),
        user_id=str(model.user_id),
        equipment_id=EquipmentId(model.equipment_id),
        quantity=model.quantity,
        notes=model.notes,
        updated_at=model.updated_at,
    )
