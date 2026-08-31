"""
UserRepository (interface) that Application depends on and Infrastructure implements.

"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.iam.domain.entities.user import User
from app.iam.domain.value_objects.email import Email
from app.iam.domain.value_objects.user_id import UserId


class UserRepository(ABC):
    @abstractmethod
    async def add(self, user: User) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: Email) -> User | None:
        ...

    @abstractmethod
    async def exists_by_email(self, email: Email) -> bool:
        ...

    @abstractmethod
    async def update(self, user: User) -> None:
        ...
