"""SQLAlchemy implementation of `UnitRepository`."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.domain.entities.unit import Unit, UnitSystem, UnitType
from app.ingredients.domain.repositories.unit_repository import UnitRepository
from app.ingredients.domain.value_objects.unit_id import UnitId
from app.ingredients.infrastructure.persistence.models.unit_model import UnitModel


class SqlAlchemyUnitRepository(UnitRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, unit_id: UnitId) -> Unit | None:
        model = await self._session.get(UnitModel, unit_id.value)
        return _to_entity(model) if model else None

    async def get_many_by_ids(self, ids: list[UnitId]) -> list[Unit]:
        if not ids:
            return []
        values = [unit_id.value for unit_id in ids]
        result = await self._session.execute(select(UnitModel).where(UnitModel.id.in_(values)))
        return [_to_entity(model) for model in result.scalars().all()]

    async def list_all(self) -> list[Unit]:
        result = await self._session.execute(select(UnitModel).order_by(UnitModel.unit_type, UnitModel.name))
        return [_to_entity(model) for model in result.scalars().all()]


def _to_entity(model: UnitModel) -> Unit:
    return Unit(
        id=UnitId(model.id),
        name=model.name,
        abbreviation=model.abbreviation,
        unit_type=UnitType(model.unit_type),
        base_factor=model.base_factor,
        unit_system=UnitSystem(model.unit_system),
    )
