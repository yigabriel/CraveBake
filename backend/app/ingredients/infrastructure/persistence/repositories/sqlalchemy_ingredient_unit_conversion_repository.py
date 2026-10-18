"""SQLAlchemy implementation of `IngredientUnitConversionRepository`."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.domain.entities.ingredient_unit_conversion import IngredientUnitConversion
from app.ingredients.domain.repositories.ingredient_unit_conversion_repository import (
    IngredientUnitConversionRepository,
)
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.value_objects.ingredient_unit_conversion_id import (
    IngredientUnitConversionId,
)
from app.ingredients.domain.value_objects.unit_id import UnitId
from app.ingredients.infrastructure.persistence.models.ingredient_unit_conversion_model import (
    IngredientUnitConversionModel,
)


class SqlAlchemyIngredientUnitConversionRepository(IngredientUnitConversionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, conversion: IngredientUnitConversion) -> None:
        self._session.add(
            IngredientUnitConversionModel(
                id=conversion.id.value,
                ingredient_id=conversion.ingredient_id.value,
                unit_id=conversion.unit_id.value,
                grams_equivalent=conversion.grams_equivalent,
            )
        )
        await self._session.flush()

    async def get_by_ingredient_and_unit(
        self, ingredient_id: IngredientId, unit_id: UnitId
    ) -> IngredientUnitConversion | None:
        result = await self._session.execute(
            select(IngredientUnitConversionModel).where(
                IngredientUnitConversionModel.ingredient_id == ingredient_id.value,
                IngredientUnitConversionModel.unit_id == unit_id.value,
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_ingredients(self, ingredient_ids: list[IngredientId]) -> list[IngredientUnitConversion]:
        if not ingredient_ids:
            return []
        result = await self._session.execute(
            select(IngredientUnitConversionModel).where(
                IngredientUnitConversionModel.ingredient_id.in_([item.value for item in ingredient_ids])
            )
        )
        return [_to_entity(model) for model in result.scalars().all()]


def _to_entity(model: IngredientUnitConversionModel) -> IngredientUnitConversion:
    return IngredientUnitConversion(
        id=IngredientUnitConversionId(model.id),
        ingredient_id=IngredientId(model.ingredient_id),
        unit_id=UnitId(model.unit_id),
        grams_equivalent=model.grams_equivalent,
    )
