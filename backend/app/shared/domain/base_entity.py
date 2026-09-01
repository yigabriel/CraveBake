from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generic, TypeVar

TId = TypeVar("TId")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BaseEntity(Generic[TId]):
    id: TId
    created_at: datetime = field(
        default_factory=_utc_now,
        kw_only=True,
    )
    updated_at: datetime = field(
        default_factory=_utc_now,
        kw_only=True,
    )

    def _touch(self) -> None:
        self.updated_at = _utc_now()