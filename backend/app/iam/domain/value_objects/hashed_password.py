"""
HashedPassword value object.

Wraps an already-hashed password string. It deliberately does NOT know how
to hash or verify passwords — that behavior lives behind the
`PasswordHasher` domain service interface, implemented with bcrypt in
Infrastructure. Keeping this VO "dumb" keeps a specific hashing algorithm
out of Domain.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.shared.exceptions.domain_exceptions import ValidationError


@dataclass(frozen=True)
class HashedPassword:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValidationError("Hashed password cannot be empty")
            
