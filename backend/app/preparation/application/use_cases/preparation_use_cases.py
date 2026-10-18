"""
Preparation use cases: start (or resume), read, history, and guided progress.

A preparation is private to its user: anyone else gets 404, so its existence
is not revealed. Every progress command returns the updated detail, so the
client can re-render the cooking screen from a single response.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.preparation.application.dto.preparation_dto import PreparationDetailDTO, PreparationSummaryDTO
from app.preparation.application.mappers.preparation_assembler import PreparationAssembler, to_summary
from app.preparation.domain.entities.preparation_session import PreparationSession, PreparationStatus, utc_now
from app.preparation.domain.exceptions import PreparationNotFoundError, PreparationRecipeNotFoundError
from app.preparation.domain.repositories.preparation_session_repository import PreparationSessionRepository
from app.preparation.domain.services.ports import RecipeSource
from app.preparation.domain.value_objects.preparation_session_id import PreparationSessionId
from app.shared.application.pagination import Page


async def load_owned_preparation(
    repository: PreparationSessionRepository, preparation_id: str, user_id: str
) -> PreparationSession:
    parsed_id = PreparationSessionId.try_from_string(preparation_id)
    session = await repository.get_by_id(parsed_id) if parsed_id else None
    if session is None or not session.is_owned_by(user_id):
        raise PreparationNotFoundError(preparation_id)
    return session


@dataclass(frozen=True)
class StartedPreparation:
    preparation: PreparationDetailDTO
    resumed: bool  # True when an in-progress preparation of the same recipe was returned instead


class StartPreparationUseCase:
    """The "Cocinar" button: starts a preparation of a recipe, or resumes the one already in progress."""

    def __init__(
        self,
        repository: PreparationSessionRepository,
        recipe_source: RecipeSource,
        assembler: PreparationAssembler,
    ) -> None:
        self._repository = repository
        self._recipe_source = recipe_source
        self._assembler = assembler

    async def execute(self, user_id: str, recipe_id: str, unit_system: str) -> StartedPreparation:
        recipe = await self._recipe_source.get_recipe_to_prepare(recipe_id, user_id)
        if recipe is None:
            raise PreparationRecipeNotFoundError(recipe_id)

        ongoing = await self._repository.find_in_progress(user_id, recipe.id)
        if ongoing is not None:
            return StartedPreparation(await self._assembler.to_detail(ongoing, unit_system, utc_now()), resumed=True)

        session = PreparationSession.start(user_id, recipe)
        await self._repository.add(session)
        return StartedPreparation(await self._assembler.to_detail(session, unit_system, utc_now()), resumed=False)


class GetPreparationUseCase:
    def __init__(self, repository: PreparationSessionRepository, assembler: PreparationAssembler) -> None:
        self._repository = repository
        self._assembler = assembler

    async def execute(self, user_id: str, preparation_id: str, unit_system: str) -> PreparationDetailDTO:
        session = await load_owned_preparation(self._repository, preparation_id, user_id)
        return await self._assembler.to_detail(session, unit_system, utc_now())


class ListPreparationsUseCase:
    """The user's cooking history, newest first; filterable by status and recipe."""

    def __init__(self, repository: PreparationSessionRepository) -> None:
        self._repository = repository

    async def execute(
        self, user_id: str, status: str | None, recipe_id: str | None, limit: int, offset: int
    ) -> Page[PreparationSummaryDTO]:
        page = await self._repository.list_by_user(
            user_id, PreparationStatus(status) if status else None, recipe_id, limit, offset
        )
        return Page(items=[to_summary(session) for session in page.items], total=page.total, limit=limit, offset=offset)


class PreparationProgressUseCases:
    """Guided-mode commands. Each one loads the session, applies one domain command and saves it."""

    def __init__(self, repository: PreparationSessionRepository, assembler: PreparationAssembler) -> None:
        self._repository = repository
        self._assembler = assembler

    async def go_to_step(self, user_id: str, preparation_id: str, step_number: int, unit_system: str):
        return await self._apply(user_id, preparation_id, unit_system, lambda s, now: s.go_to_step(step_number))

    async def complete_step(self, user_id: str, preparation_id: str, step_number: int, unit_system: str):
        return await self._apply(user_id, preparation_id, unit_system, lambda s, now: s.complete_step(step_number, now))

    async def uncomplete_step(self, user_id: str, preparation_id: str, step_number: int, unit_system: str):
        return await self._apply(user_id, preparation_id, unit_system, lambda s, now: s.uncomplete_step(step_number))

    async def start_timer(self, user_id: str, preparation_id: str, step_number: int, unit_system: str):
        return await self._apply(user_id, preparation_id, unit_system, lambda s, now: s.start_timer(step_number, now))

    async def finish(self, user_id: str, preparation_id: str, unit_system: str):
        return await self._apply(user_id, preparation_id, unit_system, lambda s, now: s.finish(now))

    async def abandon(self, user_id: str, preparation_id: str, unit_system: str):
        return await self._apply(user_id, preparation_id, unit_system, lambda s, now: s.abandon(now))

    async def _apply(self, user_id: str, preparation_id: str, unit_system: str, command) -> PreparationDetailDTO:
        session = await load_owned_preparation(self._repository, preparation_id, user_id)
        now = utc_now()
        command(session, now)
        await self._repository.update(session)
        return await self._assembler.to_detail(session, unit_system, now)
