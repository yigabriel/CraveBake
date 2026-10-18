"""SQLAlchemy implementation of `UserIngredientRepository`."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.domain.entities.user_ingredient import UserIngredient
from app.ingredients.domain.repositories.user_ingredient_repository import UserIngredientRepository
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.value_objects.unit_id import UnitId
from app.ingredients.domain.value_objects.user_ingredient_id import UserIngredientId
from app.ingredients.infrastructure.persistence.models.user_ingredient_model import (
    UserIngredientModel,
)


class SqlAlchemyUserIngredientRepository(UserIngredientRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_ingredient: UserIngredient) -> None:
        self._session.add(_to_model(user_ingredient))
        await self._session.flush()

    async def update(self, user_ingredient: UserIngredient) -> None:
        model = await self._session.get(UserIngredientModel, user_ingredient.id.value)
        if model is None:
            return
        model.quantity = user_ingredient.quantity
        model.unit_id = user_ingredient.unit_id.value if user_ingredient.unit_id else None
        await self._session.flush()

    async def remove(self, user_id: str, ingredient_id: IngredientId) -> None:
        await self._session.execute(
            delete(UserIngredientModel).where(
                UserIngredientModel.user_id == uuid.UUID(user_id),
                UserIngredientModel.ingredient_id == ingredient_id.value,
            )
        )
        await self._session.flush()

    async def get_by_user_and_ingredient(
        self, user_id: str, ingredient_id: IngredientId
    ) -> UserIngredient | None:
        result = await self._session.execute(
            select(UserIngredientModel).where(
                UserIngredientModel.user_id == uuid.UUID(user_id),
                UserIngredientModel.ingredient_id == ingredient_id.value,
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_user(self, user_id: str) -> list[UserIngredient]:
        result = await self._session.execute(
            select(UserIngredientModel).where(UserIngredientModel.user_id == uuid.UUID(user_id))
        )
        return [_to_entity(model) for model in result.scalars().all()]


def _to_entity(model: UserIngredientModel) -> UserIngredient:
    return UserIngredient(
        id=UserIngredientId(model.id),
        user_id=str(model.user_id),
        ingredient_id=IngredientId(model.ingredient_id),
        quantity=model.quantity,
        unit_id=UnitId(model.unit_id) if model.unit_id else None,
        updated_at=model.updated_at,
    )


def _to_model(user_ingredient: UserIngredient) -> UserIngredientModel:
    return UserIngredientModel(
        id=user_ingredient.id.value,
        user_id=uuid.UUID(user_ingredient.user_id),
        ingredient_id=user_ingredient.ingredient_id.value,
        quantity=user_ingredient.quantity,
        unit_id=user_ingredient.unit_id.value if user_ingredient.unit_id else None,
    )
