"""DiscoverySessionRepository — port (interface) for the DiscoverySession aggregate."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.recommendations.domain.entities.discovery_session import DiscoverySession
from app.recommendations.domain.value_objects.discovery_session_id import DiscoverySessionId


class DiscoverySessionRepository(ABC):
    @abstractmethod
    async def add(self, session: DiscoverySession) -> None:
        ...

    @abstractmethod
    async def update(self, session: DiscoverySession) -> None:
        """Persists swipes added since the session was loaded (swipes are append-only)."""

    @abstractmethod
    async def get_by_id(self, session_id: DiscoverySessionId) -> DiscoverySession | None:
        ...
