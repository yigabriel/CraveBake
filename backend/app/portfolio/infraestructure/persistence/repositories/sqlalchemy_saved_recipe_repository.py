"""SQLAlchemy implementation of `SavedRecipeRepository`."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.domain.entities.saved_recipe import SavedRecipe
from app.portfolio.domain.repositories.saved_recipe_repository import SavedRecipeRepository
from app.portfolio.domain.value_objects.saved_recipe_id import SavedRecipeId
from app.portfolio.infraestructure.persistence.models.saved_recipe_model import SavedRecipeModel
from app.shared.domain.value_objects.entity_id import EntityId


class SqlAlchemySavedRecipeRepository(SavedRecipeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, saved_recipe: SavedRecipe) -> None:
        self._session.add(
            SavedRecipeModel(
                id=saved_recipe.id.value,
                user_id=uuid.UUID(saved_recipe.user_id),
                recipe_id=uuid.UUID(saved_recipe.recipe_id),
                created_at=saved_recipe.saved_at,
            )
        )
        await self._session.flush()

    async def remove(self, user_id: str, recipe_id: str) -> None:
        recipe_uuid = _parse_uuid(recipe_id)
        if recipe_uuid is None:
            return
        await self._session.execute(
            delete(SavedRecipeModel).where(
                SavedRecipeModel.user_id == uuid.UUID(user_id),
                SavedRecipeModel.recipe_id == recipe_uuid,
            )
        )
        await self._session.flush()

    async def get(self, user_id: str, recipe_id: str) -> SavedRecipe | None:
        recipe_uuid = _parse_uuid(recipe_id)
        if recipe_uuid is None:
            return None
        result = await self._session.execute(
            select(SavedRecipeModel).where(
                SavedRecipeModel.user_id == uuid.UUID(user_id),
                SavedRecipeModel.recipe_id == recipe_uuid,
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_user(self, user_id: str) -> list[SavedRecipe]:
        result = await self._session.execute(
            select(SavedRecipeModel)
            .where(SavedRecipeModel.user_id == uuid.UUID(user_id))
            .order_by(SavedRecipeModel.created_at.desc())
        )
        return [_to_entity(model) for model in result.scalars().all()]

    async def list_by_user_and_recipes(self, user_id: str, recipe_ids: list[str]) -> list[SavedRecipe]:
        recipe_uuids = [parsed for raw in recipe_ids if (parsed := _parse_uuid(raw)) is not None]
        if not recipe_uuids:
            return []
        result = await self._session.execute(
            select(SavedRecipeModel).where(
                SavedRecipeModel.user_id == uuid.UUID(user_id),
                SavedRecipeModel.recipe_id.in_(recipe_uuids),
            )
        )
        return [_to_entity(model) for model in result.scalars().all()]


def _parse_uuid(raw: str) -> uuid.UUID | None:
    parsed = EntityId.try_from_string(raw)
    return parsed.value if parsed else None


def _to_entity(model: SavedRecipeModel) -> SavedRecipe:
    return SavedRecipe(
        id=SavedRecipeId(model.id),
        user_id=str(model.user_id),
        recipe_id=str(model.recipe_id),
        saved_at=model.created_at,
    )
