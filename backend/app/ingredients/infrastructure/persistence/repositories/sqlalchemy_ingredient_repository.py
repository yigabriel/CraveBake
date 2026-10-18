"""SQLAlchemy implementation of `IngredientRepository`."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.domain.entities.ingredient import Ingredient
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.infrastructure.persistence.models.ingredient_model import IngredientModel


class SqlAlchemyIngredientRepository(IngredientRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, ingredient: Ingredient) -> None:
        self._session.add(_to_model(ingredient))
        await self._session.flush()

    async def get_by_id(self, ingredient_id: IngredientId) -> Ingredient | None:
        model = await self._session.get(IngredientModel, ingredient_id.value)
        return _to_entity(model) if model else None

    async def get_many_by_ids(self, ids: list[IngredientId]) -> list[Ingredient]:
        if not ids:
            return []
        values = [ingredient_id.value for ingredient_id in ids]
        result = await self._session.execute(select(IngredientModel).where(IngredientModel.id.in_(values)))
        return [_to_entity(model) for model in result.scalars().all()]

    async def exists_by_name(self, name: str) -> bool:
        result = await self._session.execute(
            select(IngredientModel.id).where(func.lower(IngredientModel.name) == name.lower())
        )
        return result.scalar_one_or_none() is not None

    async def search(
        self, query: str | None, category: str | None, limit: int, offset: int
    ) -> list[Ingredient]:
        statement = _filtered(select(IngredientModel), query, category)
        statement = statement.order_by(IngredientModel.name).limit(limit).offset(offset)

        result = await self._session.execute(statement)
        return [_to_entity(model) for model in result.scalars().all()]

    async def count(self, query: str | None, category: str | None) -> int:
        statement = _filtered(select(func.count()).select_from(IngredientModel), query, category)
        return (await self._session.execute(statement)).scalar_one()

    async def list_distinct_categories(self) -> list[tuple[str, int]]:
        statement = (
            select(IngredientModel.default_category, func.count(IngredientModel.id))
            .where(IngredientModel.default_category.isnot(None))
            .group_by(IngredientModel.default_category)
            .order_by(IngredientModel.default_category)
        )
        result = await self._session.execute(statement)
        return [(name, count) for name, count in result.all()]


def _filtered(statement, query: str | None, category: str | None):
    if query:
        statement = statement.where(IngredientModel.name.ilike(f"%{query}%"))
    if category:
        statement = statement.where(IngredientModel.default_category == category)
    return statement


def _to_entity(model: IngredientModel) -> Ingredient:
    return Ingredient(
        id=IngredientId(model.id),
        name=model.name,
        description=model.description,
        default_category=model.default_category,
        created_at=model.created_at,
    )


def _to_model(ingredient: Ingredient) -> IngredientModel:
    return IngredientModel(
        id=ingredient.id.value,
        name=ingredient.name,
        description=ingredient.description,
        default_category=ingredient.default_category,
    )
