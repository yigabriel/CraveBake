"""UserId value object: wraps a UUID so entities never pass raw strings around."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class UserId:
    value: uuid.UUID = field(default_factory=uuid.uuid4)

    @classmethod
    def from_string(cls, raw: str) -> "UserId":
        return cls(uuid.UUID(raw))

    def __str__(self) -> str:
        return str(self.value)
