"""PreparationSessionRepository — port (interface) for the PreparationSession aggregate."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.preparation.domain.entities.preparation_session import PreparationSession, PreparationStatus
from app.preparation.domain.value_objects.preparation_session_id import PreparationSessionId


@dataclass(frozen=True)
class PreparationPage:
    items: list[PreparationSession]
    total: int


class PreparationSessionRepository(ABC):
    @abstractmethod
    async def add(self, session: PreparationSession) -> None:
        ...

    @abstractmethod
    async def update(self, session: PreparationSession) -> None:
        """Persists status, current step and per-step progress (the copied recipe never changes)."""

    @abstractmethod
    async def get_by_id(self, session_id: PreparationSessionId) -> PreparationSession | None:
        ...

    @abstractmethod
    async def find_in_progress(self, user_id: str, recipe_id: str) -> PreparationSession | None:
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        status: PreparationStatus | None,
        recipe_id: str | None,
        limit: int,
        offset: int,
    ) -> PreparationPage:
        """The user's preparations, newest first (their cooking history)."""
