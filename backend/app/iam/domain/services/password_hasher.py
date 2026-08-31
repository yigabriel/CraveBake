"""
PasswordHasher — domain service interface.

Domain needs the *concept* of hashing/verifying passwords to enforce its
invariants, but not a specific algorithm. bcrypt (or any other choice) is
an Infrastructure detail, implemented in `infrastructure/security`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.iam.domain.value_objects.hashed_password import HashedPassword
from app.iam.domain.value_objects.plain_password import PlainPassword


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain_password: PlainPassword) -> HashedPassword:
        ...

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: HashedPassword) -> bool:
        ...
