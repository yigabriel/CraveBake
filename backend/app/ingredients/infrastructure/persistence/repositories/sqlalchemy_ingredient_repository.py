"""SQLAlchemy implementation of `IngredientRepository`."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.domain.entities.ingredient import Ingredient
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.infrastructure.persistence.models.ingredient_model import IngredientModel
from app.shared.database.localized_name import name_columns, name_contains, name_equals, original_name
from app.ingredients.infrastructure.persistence.models.ingredient_category_model import IngredientCategoryModel
from app.shared.domain.value_objects.localized_text import LocalizedText


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
        result = await self._session.execute(select(IngredientModel.id).where(name_equals(IngredientModel, name)).limit(1))
        return result.scalar_one_or_none() is not None

    async def search(
        self, query: str | None, category: str | None, limit: int, offset: int
    ) -> list[Ingredient]:
        statement = _filtered(select(IngredientModel), query, category)
        statement = statement.order_by(original_name(IngredientModel)).limit(limit).offset(offset)

        result = await self._session.execute(statement)
        return [_to_entity(model) for model in result.scalars().all()]

    async def count(self, query: str | None, category: str | None) -> int:
        statement = _filtered(select(func.count()).select_from(IngredientModel), query, category)
        return (await self._session.execute(statement)).scalar_one()

    async def list_distinct_categories(self) -> list[tuple[str, LocalizedText, int]]:
        statement = (
            select(IngredientModel.default_category, IngredientCategoryModel, func.count(IngredientModel.id))
            .outerjoin(IngredientCategoryModel, IngredientCategoryModel.code == IngredientModel.default_category)
            .where(IngredientModel.default_category.isnot(None))
            .group_by(IngredientModel.default_category, IngredientCategoryModel.id)
            .order_by(IngredientModel.default_category)
        )
        result = await self._session.execute(statement)
        return [(code, _category_name(code, category), count) for code, category, count in result.all()]


def _filtered(statement, query: str | None, category: str | None):
    if query:
        statement = statement.where(name_contains(IngredientModel, query))
    if category:
        statement = statement.where(IngredientModel.default_category == category)
    return statement


def _category_name(code: str | None, category: IngredientCategoryModel | None) -> LocalizedText | None:
    """A known code has its localized name; an unknown one (old free text) is shown as written."""
    if code is None:
        return None
    return category.localized_name if category else LocalizedText.of(code)


def _to_entity(model: IngredientModel) -> Ingredient:
    return Ingredient(
        id=IngredientId(model.id),
        name=model.localized_name,
        description=model.description,
        default_category=model.default_category,
        category_name=_category_name(model.default_category, model.category),
        created_at=model.created_at,
    )


def _to_model(ingredient: Ingredient) -> IngredientModel:
    return IngredientModel(
        id=ingredient.id.value,
        **name_columns(ingredient.name),
        description=ingredient.description,
        default_category=ingredient.default_category,
    )
