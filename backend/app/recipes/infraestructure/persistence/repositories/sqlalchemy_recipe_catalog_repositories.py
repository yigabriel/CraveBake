"""SQLAlchemy implementations of the recipe catalog repositories (categories, difficulties, tags)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.recipes.domain.entities.difficulty import Difficulty
from app.recipes.domain.entities.recipe_category import RecipeCategory
from app.recipes.domain.entities.recipe_tag import RecipeTag, TagGroup
from app.recipes.domain.repositories.recipe_catalog_repositories import (
    DifficultyRepository,
    RecipeCategoryRepository,
    RecipeTagRepository,
)
from app.recipes.domain.value_objects.difficulty_id import DifficultyId
from app.recipes.domain.value_objects.recipe_category_id import RecipeCategoryId
from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId
from app.recipes.infraestructure.persistence.models.difficulty_model import DifficultyModel
from app.recipes.infraestructure.persistence.models.recipe_category_model import RecipeCategoryModel
from app.recipes.infraestructure.persistence.models.tag_models import TagModel


class SqlAlchemyRecipeCategoryRepository(RecipeCategoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, category_id: RecipeCategoryId) -> RecipeCategory | None:
        model = await self._session.get(RecipeCategoryModel, category_id.value)
        return RecipeCategory(id=RecipeCategoryId(model.id), name=model.name) if model else None

    async def list_all(self) -> list[RecipeCategory]:
        result = await self._session.execute(select(RecipeCategoryModel).order_by(RecipeCategoryModel.name))
        return [RecipeCategory(id=RecipeCategoryId(model.id), name=model.name) for model in result.scalars().all()]


class SqlAlchemyDifficultyRepository(DifficultyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, difficulty_id: DifficultyId) -> Difficulty | None:
        model = await self._session.get(DifficultyModel, difficulty_id.value)
        return _to_difficulty(model) if model else None

    async def list_all(self) -> list[Difficulty]:
        result = await self._session.execute(select(DifficultyModel).order_by(DifficultyModel.level_order))
        return [_to_difficulty(model) for model in result.scalars().all()]


def _to_difficulty(model: DifficultyModel) -> Difficulty:
    return Difficulty(id=DifficultyId(model.id), name=model.name, level_order=model.level_order)


class SqlAlchemyRecipeTagRepository(RecipeTagRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_many_by_ids(self, tag_ids: list[RecipeTagId]) -> list[RecipeTag]:
        if not tag_ids:
            return []
        result = await self._session.execute(
            select(TagModel).where(TagModel.id.in_([tag_id.value for tag_id in tag_ids]))
        )
        return [_to_tag(model) for model in result.scalars().all()]

    async def list_all(self) -> list[RecipeTag]:
        result = await self._session.execute(select(TagModel).order_by(TagModel.tag_group, TagModel.name))
        return [_to_tag(model) for model in result.scalars().all()]


def _to_tag(model: TagModel) -> RecipeTag:
    return RecipeTag(id=RecipeTagId(model.id), name=model.name, group=TagGroup(model.tag_group))
