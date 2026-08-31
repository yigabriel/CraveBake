"""
User entity - the aggregate root of the IAM bounded context.

Encapsulates identity and account-state invariants as plain Python
behavior. Application use cases manipulate it exclusively through the `UserRepository` interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.iam.domain.value_objects.email import Email
from app.iam.domain.value_objects.hashed_password import HashedPassword
from app.iam.domain.value_objects.unit_system_preference import UnitSystemPreference
from app.iam.domain.value_objects.user_id import UserId
from backend.app.iam.domain.value_objects.language_preference import LanguagePreference
from backend.app.shared.domain.base_entity import BaseEntity

@dataclass
class User(BaseEntity[UserId]):
    email: Email
    hashed_password: HashedPassword
    full_name: str
    avatar_url: str | None = None
    preferred_unit_system: UnitSystemPreference = UnitSystemPreference.METRIC
    preferred_language: LanguagePreference = LanguagePreference.ENGLISH
    is_active: bool = True

    @classmethod
    def register(
        cls, #cls representa la clase actual y permite crear nuevas instancias desde un método de clase.
        email: Email,
        hashed_password: HashedPassword,
        full_name: str,
        preferred_unit_system: UnitSystemPreference = UnitSystemPreference.METRIC,
        preferred_language: LanguagePreference = LanguagePreference.ENGLISH,
    ) -> "User":
        
        return cls(
            id=UserId(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name.strip(),
            preferred_unit_system=preferred_unit_system,
            preferred_language=preferred_language,
        )

    def change_password(self, new_hashed_password: HashedPassword) -> None:
        self.hashed_password = new_hashed_password
        self._touch()

    def update_profile(self, full_name: str | None = None, avatar_url: str | None = None) -> None:
        if full_name is not None:
            self.full_name = full_name.strip()
        if avatar_url is not None:
            self.avatar_url = avatar_url
        self._touch()

    def change_unit_preference(self, preference: UnitSystemPreference) -> None:
        self.preferred_unit_system = preference
        self._touch()

    def change_language_preference(self, language: str) -> None:
        self.preferred_language = language
        self._touch()

    def deactivate(self) -> None:
        self.is_active = False
        self._touch()

    def activate(self) -> None:
        self.is_active = True
        self._touch()