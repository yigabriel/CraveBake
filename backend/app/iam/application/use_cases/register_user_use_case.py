"""
RegisterUserUseCase.

Orchestrates registration: validates email uniqueness, builds the domain objects, delegates hashing to `PasswordHasher`, and persists via
`UserRepository`.
"""
from __future__ import annotations

from app.iam.application.dto.register_user_dto import RegisterUserDTO
from app.iam.application.dto.user_dto import UserDTO
from app.iam.application.mappers.user_mapper import user_to_dto
from app.iam.domain.entities.user import User
from app.iam.domain.exceptions import UserAlreadyExistsError
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.services.password_hasher import PasswordHasher
from app.iam.domain.value_objects.email import Email
from app.iam.domain.value_objects.plain_password import PlainPassword


class RegisterUserUseCase:
    def __init__(self, user_repository: UserRepository, password_hasher: PasswordHasher) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher

    async def execute(self, dto: RegisterUserDTO) -> UserDTO:
        email = Email(dto.email)

        if await self._user_repository.exists_by_email(email):
            raise UserAlreadyExistsError(dto.email)

        plain_password = PlainPassword(dto.password)
        hashed_password = self._password_hasher.hash(plain_password)

        user = User.register(email=email, hashed_password=hashed_password, full_name=dto.full_name)
        await self._user_repository.add(user)

        return user_to_dto(user)
