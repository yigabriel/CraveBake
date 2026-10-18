"""SQLAlchemy implementation of `PreparationSessionRepository`."""
from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.preparation.domain.entities.preparation_session import (
    PreparationSession,
    PreparationStatus,
    PreparedIngredient,
    PreparedStep,
)
from app.preparation.domain.repositories.preparation_session_repository import (
    PreparationPage,
    PreparationSessionRepository,
)
from app.preparation.domain.value_objects.preparation_session_id import PreparationSessionId
from app.preparation.infraestructure.persistence.models.preparation_models import (
    PreparationIngredientModel,
    PreparationSessionModel,
    PreparationStepModel,
)
from app.shared.domain.value_objects.entity_id import EntityId


class SqlAlchemyPreparationSessionRepository(PreparationSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, preparation: PreparationSession) -> None:
        self._session.add(
            PreparationSessionModel(
                id=preparation.id.value,
                user_id=uuid.UUID(preparation.user_id),
                recipe_id=uuid.UUID(preparation.recipe_id),
                recipe_title=preparation.recipe_title,
                cover_photo_url=preparation.cover_photo_url,
                servings=preparation.servings,
                status=preparation.status.value,
                current_step_number=preparation.current_step_number,
                finished_at=preparation.finished_at,
                created_at=preparation.started_at,
            )
        )
        await self._session.flush()
        for step in preparation.steps:
            self._session.add(
                PreparationStepModel(
                    id=uuid.uuid4(),
                    session_id=preparation.id.value,
                    step_number=step.step_number,
                    title=step.title,
                    instructions=step.instructions,
                    timer_seconds=step.timer_seconds,
                    photo_url=step.photo_url,
                    source_step_id=uuid.UUID(step.source_step_id) if step.source_step_id else None,
                    completed_at=step.completed_at,
                    timer_started_at=step.timer_started_at,
                )
            )
        for line in preparation.ingredients:
            self._session.add(
                PreparationIngredientModel(
                    id=uuid.uuid4(),
                    session_id=preparation.id.value,
                    ingredient_id=uuid.UUID(line.ingredient_id),
                    ingredient_name=line.ingredient_name,
                    quantity=line.quantity,
                    unit_id=uuid.UUID(line.unit_id),
                    unit_abbreviation=line.unit_abbreviation,
                    notes=line.notes,
                    position=line.position,
                )
            )
        await self._session.flush()

    async def update(self, preparation: PreparationSession) -> None:
        model = await self._session.get(PreparationSessionModel, preparation.id.value)
        if model is None:
            return
        model.status = preparation.status.value
        model.current_step_number = preparation.current_step_number
        model.finished_at = preparation.finished_at

        progress = {step.step_number: step for step in preparation.steps}
        result = await self._session.execute(
            select(PreparationStepModel).where(PreparationStepModel.session_id == preparation.id.value)
        )
        for step_model in result.scalars().all():
            step = progress[step_model.step_number]
            step_model.completed_at = step.completed_at
            step_model.timer_started_at = step.timer_started_at
        await self._session.flush()

    async def get_by_id(self, session_id: PreparationSessionId) -> PreparationSession | None:
        model = await self._session.get(PreparationSessionModel, session_id.value)
        if model is None:
            return None
        return (await self._to_entities([model]))[0]

    async def find_in_progress(self, user_id: str, recipe_id: str) -> PreparationSession | None:
        recipe = EntityId.try_from_string(recipe_id)
        if recipe is None:
            return None
        result = await self._session.execute(
            select(PreparationSessionModel).where(
                PreparationSessionModel.user_id == uuid.UUID(user_id),
                PreparationSessionModel.recipe_id == recipe.value,
                PreparationSessionModel.status == PreparationStatus.IN_PROGRESS.value,
            )
        )
        model = result.scalar_one_or_none()
        return (await self._to_entities([model]))[0] if model else None

    async def list_by_user(
        self,
        user_id: str,
        status: PreparationStatus | None,
        recipe_id: str | None,
        limit: int,
        offset: int,
    ) -> PreparationPage:
        conditions = [PreparationSessionModel.user_id == uuid.UUID(user_id)]
        if status is not None:
            conditions.append(PreparationSessionModel.status == status.value)
        if recipe_id is not None:
            recipe = EntityId.try_from_string(recipe_id)
            if recipe is None:
                return PreparationPage(items=[], total=0)
            conditions.append(PreparationSessionModel.recipe_id == recipe.value)

        total = (
            await self._session.execute(
                select(func.count()).select_from(PreparationSessionModel).where(*conditions)
            )
        ).scalar_one()
        result = await self._session.execute(
            select(PreparationSessionModel)
            .where(*conditions)
            .order_by(PreparationSessionModel.created_at.desc(), PreparationSessionModel.id)
            .limit(limit)
            .offset(offset)
        )
        return PreparationPage(items=await self._to_entities(list(result.scalars().all())), total=total)

    async def _to_entities(self, models: list[PreparationSessionModel]) -> list[PreparationSession]:
        if not models:
            return []
        ids = [model.id for model in models]
        steps: dict[uuid.UUID, list[PreparationStepModel]] = defaultdict(list)
        for step in (
            await self._session.execute(select(PreparationStepModel).where(PreparationStepModel.session_id.in_(ids)))
        ).scalars():
            steps[step.session_id].append(step)
        ingredients: dict[uuid.UUID, list[PreparationIngredientModel]] = defaultdict(list)
        for line in (
            await self._session.execute(
                select(PreparationIngredientModel).where(PreparationIngredientModel.session_id.in_(ids))
            )
        ).scalars():
            ingredients[line.session_id].append(line)

        return [
            PreparationSession(
                id=PreparationSessionId(model.id),
                user_id=str(model.user_id),
                recipe_id=str(model.recipe_id),
                recipe_title=model.recipe_title,
                cover_photo_url=model.cover_photo_url,
                servings=model.servings,
                status=PreparationStatus(model.status),
                current_step_number=model.current_step_number,
                ingredients=[
                    PreparedIngredient(
                        ingredient_id=str(line.ingredient_id),
                        ingredient_name=line.ingredient_name,
                        quantity=line.quantity,
                        unit_id=str(line.unit_id),
                        unit_abbreviation=line.unit_abbreviation,
                        notes=line.notes,
                        position=line.position,
                    )
                    for line in sorted(ingredients[model.id], key=lambda line: line.position)
                ],
                steps=[
                    PreparedStep(
                        step_number=step.step_number,
                        instructions=step.instructions,
                        title=step.title,
                        timer_seconds=step.timer_seconds,
                        photo_url=step.photo_url,
                        source_step_id=str(step.source_step_id) if step.source_step_id else None,
                        completed_at=step.completed_at,
                        timer_started_at=step.timer_started_at,
                    )
                    for step in sorted(steps[model.id], key=lambda step: step.step_number)
                ],
                started_at=model.created_at,
                finished_at=model.finished_at,
            )
            for model in models
        ]
