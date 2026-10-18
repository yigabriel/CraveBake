"""UserId value object: wraps a UUID so entities never pass raw strings around."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.shared.exceptions.domain_exceptions import ValidationError


@dataclass(frozen=True)
class UserId:
    value: uuid.UUID = field(default_factory=uuid.uuid4)

    @classmethod
    def from_string(cls, raw: str) -> "UserId":
        try:
            return cls(uuid.UUID(raw))
        except (ValueError, AttributeError, TypeError) as error:
            raise ValidationError(f"'{raw}' is not a valid user id") from error

    def __str__(self) -> str:
        return str(self.value)
