"""
PlainPassword value object.

Validates password strength rules at the moment a user submits a raw
password (registration, password change) — before it is ever hashed. This
is where the domain rule "what counts as an acceptable password" lives,
independent of whichever hashing algorithm Infrastructure ends up using.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.shared.exceptions.domain_exceptions import ValidationError

_MIN_LENGTH = 8


@dataclass(frozen=True)
class PlainPassword:
    value: str

    def __post_init__(self) -> None:
        if len(self.value) < _MIN_LENGTH:
            raise ValidationError(f"Password must be at least {_MIN_LENGTH} characters long")
        if not any(char.isdigit() for char in self.value):
            raise ValidationError("Password must contain at least one digit")
        if not any(char.isalpha() for char in self.value):
            raise ValidationError("Password must contain at least one letter")
