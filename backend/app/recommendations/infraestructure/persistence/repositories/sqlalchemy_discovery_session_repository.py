"""SQLAlchemy implementation of `DiscoverySessionRepository`."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.recommendations.domain.entities.discovery_session import (
    DiscoverySession,
    IngredientSource,
    Swipe,
    SwipeAction,
)
from app.recommendations.domain.repositories.discovery_session_repository import DiscoverySessionRepository
from app.recommendations.domain.value_objects.discovery_session_id import DiscoverySessionId
from app.recommendations.domain.value_objects.swipe_id import SwipeId
from app.recommendations.infraestructure.persistence.models.discovery_models import (
    DiscoverySessionModel,
    DiscoverySwipeModel,
)


class SqlAlchemyDiscoverySessionRepository(DiscoverySessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, discovery_session: DiscoverySession) -> None:
        self._session.add(
            DiscoverySessionModel(
                id=discovery_session.id.value,
                user_id=uuid.UUID(discovery_session.user_id),
                ingredient_source=discovery_session.ingredient_source.value,
                ingredient_ids=list(discovery_session.ingredient_ids),
                min_score=discovery_session.min_score,
                category_id=uuid.UUID(discovery_session.category_id) if discovery_session.category_id else None,
                tag_ids=list(discovery_session.tag_ids),
                created_at=discovery_session.created_at,
            )
        )
        await self._session.flush()
        await self.update(discovery_session)

    async def update(self, discovery_session: DiscoverySession) -> None:
        result = await self._session.execute(
            select(DiscoverySwipeModel.id).where(DiscoverySwipeModel.session_id == discovery_session.id.value)
        )
        persisted = set(result.scalars().all())
        for swipe in discovery_session.swipes:
            if swipe.id.value not in persisted:
                self._session.add(
                    DiscoverySwipeModel(
                        id=swipe.id.value,
                        session_id=discovery_session.id.value,
                        recipe_id=uuid.UUID(swipe.recipe_id),
                        action=swipe.action.value,
                        compatibility_score=swipe.compatibility_score,
                        created_at=swipe.created_at,
                    )
                )
        await self._session.flush()

    async def get_by_id(self, session_id: DiscoverySessionId) -> DiscoverySession | None:
        model = await self._session.get(DiscoverySessionModel, session_id.value)
        if model is None:
            return None
        result = await self._session.execute(
            select(DiscoverySwipeModel)
            .where(DiscoverySwipeModel.session_id == model.id)
            .order_by(DiscoverySwipeModel.created_at)
        )
        return DiscoverySession(
            id=DiscoverySessionId(model.id),
            user_id=str(model.user_id),
            ingredient_source=IngredientSource(model.ingredient_source),
            ingredient_ids=list(model.ingredient_ids),
            min_score=float(model.min_score),
            category_id=str(model.category_id) if model.category_id else None,
            tag_ids=list(model.tag_ids),
            swipes=[
                Swipe(
                    id=SwipeId(swipe.id),
                    recipe_id=str(swipe.recipe_id),
                    action=SwipeAction(swipe.action),
                    compatibility_score=float(swipe.compatibility_score),
                    created_at=swipe.created_at,
                )
                for swipe in result.scalars().all()
            ],
            created_at=model.created_at,
        )
