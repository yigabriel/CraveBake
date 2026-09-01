"""
SQLAlchemy implementation of `UserRepository`.

Translates between the persistence model (`UserModel`) and the domain
entity (`User`). This is the only place in the codebase where that mapping
happens, and the only place in IAM that knows SQLAlchemy exists.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.iam.domain.entities.user import User
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.value_objects.email import Email
from app.iam.domain.value_objects.hashed_password import HashedPassword
from app.iam.domain.value_objects.unit_system_preference import UnitSystemPreference
from app.iam.domain.value_objects.user_id import UserId
from app.iam.infraestructure.persistence.models.user_model import UserModel
from app.iam.domain.value_objects.language_preference import LanguagePreference




class SqlAlchemyUserRepository(UserRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(_to_model(user))
        await self._session.flush()

    async def get_by_id(self, user_id: UserId) -> User | None:
        model = await self._session.get(UserModel, user_id.value)
        return _to_entity(model) if model else None

    async def get_by_email(self, email: Email) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(
                UserModel.email == email.value
            )
        )
        model = result.scalar_one_or_none()

        return _to_entity(model) if model else None

    async def exists_by_email(self, email: Email) -> bool:
        result = await self._session.execute(
            select(UserModel.id).where(
                UserModel.email == email.value
            )
        )

        return result.scalar_one_or_none() is not None

    async def update(self, user: User) -> None:
        model = await self._session.get(
            UserModel,
            user.id.value
        )

        if model is None:
            return

        model.email = user.email.value
        model.hashed_password = user.hashed_password.value
        model.full_name = user.full_name
        model.avatar_url = user.avatar_url
        model.preferred_unit_system = user.preferred_unit_system.value
        model.preferred_language = user.preferred_language.value
        model.is_active = user.is_active

        await self._session.flush()


def _to_entity(model: UserModel) -> User:
    return User(
        id=UserId(model.id),
        email=Email(model.email),
        hashed_password=HashedPassword(model.hashed_password),
        full_name=model.full_name,
        avatar_url=model.avatar_url,
        preferred_unit_system=UnitSystemPreference(
            model.preferred_unit_system
        ),
        preferred_language=LanguagePreference(
            model.preferred_language
        ),
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id.value,
        email=user.email.value,
        hashed_password=user.hashed_password.value,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        preferred_unit_system=user.preferred_unit_system.value,
        preferred_language=user.preferred_language.value,
        is_active=user.is_active,
    )