"""
Discovery session use cases: start one, read it, list its swipes.

A session is private to its user: anyone else gets 404, so its existence
is not revealed.
"""
from __future__ import annotations

from app.recommendations.application.dto.recommendation_dto import (
    DiscoverySessionDTO,
    NamedRefDTO,
    StartSessionDTO,
    SwipeDTO,
)
from app.recommendations.domain.entities.discovery_session import DiscoverySession, Swipe, SwipeAction
from app.recommendations.domain.exceptions import (
    DiscoverySessionNotFoundError,
    SelectedCategoryNotFoundError,
    SelectedIngredientNotFoundError,
    SelectedTagNotFoundError,
)
from app.recommendations.domain.repositories.discovery_session_repository import DiscoverySessionRepository
from app.recommendations.domain.services.ports import KitchenCatalog, RecipeCandidateSource
from app.recommendations.domain.value_objects.discovery_session_id import DiscoverySessionId
from app.shared.application.pagination import Page
from app.shared.domain.value_objects.entity_id import EntityId


async def load_owned_session(
    repository: DiscoverySessionRepository, session_id: str, user_id: str
) -> DiscoverySession:
    parsed_id = DiscoverySessionId.try_from_string(session_id)
    session = await repository.get_by_id(parsed_id) if parsed_id else None
    if session is None or not session.is_owned_by(user_id):
        raise DiscoverySessionNotFoundError(session_id)
    return session


async def session_to_dto(
    session: DiscoverySession, kitchen: KitchenCatalog, recipe_source: RecipeCandidateSource
) -> DiscoverySessionDTO:
    ingredient_names = await kitchen.ingredient_names(session.ingredient_ids)
    category_names = await recipe_source.category_names() if session.category_id else {}
    tag_names = await recipe_source.tag_names() if session.tag_ids else {}
    counts = session.swipe_counts()
    return DiscoverySessionDTO(
        id=str(session.id),
        ingredient_source=session.ingredient_source.value,
        ingredients=_named_refs(session.ingredient_ids, ingredient_names),
        category=NamedRefDTO(id=session.category_id, name=category_names[session.category_id])
        if session.category_id in category_names
        else None,
        tags=_named_refs(session.tag_ids, tag_names),
        min_score=session.min_score,
        discarded_count=counts[SwipeAction.DISCARDED],
        saved_count=counts[SwipeAction.SAVED],
        selected_count=counts[SwipeAction.SELECTED],
        created_at=session.created_at,
    )


def swipe_to_dto(swipe: Swipe) -> SwipeDTO:
    return SwipeDTO(
        id=str(swipe.id),
        recipe_id=swipe.recipe_id,
        action=swipe.action.value,
        compatibility_score=swipe.compatibility_score,
        created_at=swipe.created_at,
    )


class StartDiscoverySessionUseCase:
    """Starts "¿Qué quiero cocinar?" with the selected ingredients (or the pantry) and optional filters."""

    def __init__(
        self,
        session_repository: DiscoverySessionRepository,
        kitchen: KitchenCatalog,
        recipe_source: RecipeCandidateSource,
    ) -> None:
        self._session_repository = session_repository
        self._kitchen = kitchen
        self._recipe_source = recipe_source

    async def execute(self, dto: StartSessionDTO) -> DiscoverySessionDTO:
        selected = [_canonical(raw) for raw in dto.ingredient_ids]
        if selected:
            known = await self._kitchen.ingredient_names(selected)
            for raw, ingredient_id in zip(dto.ingredient_ids, selected):
                if ingredient_id not in known:
                    raise SelectedIngredientNotFoundError(raw)
            pantry: list[str] = []
        else:
            pantry = await self._kitchen.pantry_ingredient_ids(dto.user_id)

        category_id = _canonical(dto.category_id) if dto.category_id else None
        if category_id is not None and category_id not in await self._recipe_source.category_names():
            raise SelectedCategoryNotFoundError(dto.category_id)

        tag_ids = [_canonical(raw) for raw in dto.tag_ids]
        if tag_ids:
            known_tags = await self._recipe_source.tag_names()
            for raw, tag_id in zip(dto.tag_ids, tag_ids):
                if tag_id not in known_tags:
                    raise SelectedTagNotFoundError(raw)

        session = DiscoverySession.start(
            dto.user_id, selected, pantry, dto.min_score, category_id=category_id, tag_ids=tag_ids
        )
        await self._session_repository.add(session)
        return await session_to_dto(session, self._kitchen, self._recipe_source)


class GetDiscoverySessionUseCase:
    def __init__(
        self,
        session_repository: DiscoverySessionRepository,
        kitchen: KitchenCatalog,
        recipe_source: RecipeCandidateSource,
    ) -> None:
        self._session_repository = session_repository
        self._kitchen = kitchen
        self._recipe_source = recipe_source

    async def execute(self, user_id: str, session_id: str) -> DiscoverySessionDTO:
        session = await load_owned_session(self._session_repository, session_id, user_id)
        return await session_to_dto(session, self._kitchen, self._recipe_source)


class ListSwipesUseCase:
    """The swipes of a session, newest first — e.g. `action=selected` lists what the user wants to cook."""

    def __init__(self, session_repository: DiscoverySessionRepository) -> None:
        self._session_repository = session_repository

    async def execute(
        self, user_id: str, session_id: str, action: str | None = None, limit: int = 20, offset: int = 0
    ) -> Page[SwipeDTO]:
        session = await load_owned_session(self._session_repository, session_id, user_id)
        swipes = [swipe for swipe in session.swipes if action is None or swipe.action == SwipeAction(action)]
        swipes.sort(key=lambda swipe: swipe.created_at, reverse=True)
        return Page(
            items=[swipe_to_dto(swipe) for swipe in swipes[offset : offset + limit]],
            total=len(swipes),
            limit=limit,
            offset=offset,
        )


def _named_refs(ids: list[str], names: dict) -> list[NamedRefDTO]:
    return sorted(
        (NamedRefDTO(id=item_id, name=names[item_id]) for item_id in ids if item_id in names),
        # By the name as originally written: the viewer's language is unknown here.
        key=lambda ref: str(ref.name).lower(),
    )


def _canonical(raw_id: str) -> str:
    parsed = EntityId.try_from_string(raw_id)
    return str(parsed) if parsed else raw_id
