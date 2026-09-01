from __future__ import annotations

from app.iam.application.dto.change_password_dto import ChangePasswordDTO
from app.iam.application.dto.user_dto import UserDTO
from app.iam.application.mappers.user_mapper import user_to_dto
from app.iam.domain.exceptions import (
    InvalidTokenError,
    UserNotFoundError,
)
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.services.password_hasher import PasswordHasher
from app.iam.domain.services.token_service import TokenService
from app.iam.domain.value_objects.plain_password import PlainPassword


class ChangePasswordUseCase:

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service

    async def execute(
        self,
        access_token: str,
        dto: ChangePasswordDTO,
    ) -> UserDTO:

        # 1. Validar y obtener el usuario desde el token
        try:
            payload = self._token_service.decode_access_token(access_token)
        except Exception as error:
            raise InvalidTokenError() from error

        user = await self._user_repository.get_by_id(payload.user_id)

        if user is None:
            raise UserNotFoundError(str(payload.user_id))

        # 2. Convertir las contraseñas a Value Objects
        current_password = PlainPassword(dto.current_password)
        new_password = PlainPassword(dto.new_password)

        # 3. Verificar la contraseña actual
        if not self._password_hasher.verify(
            dto.current_password,
            user.hashed_password,
        ):
            raise InvalidTokenError()

        new_password = PlainPassword(dto.new_password)

        new_hashed_password = self._password_hasher.hash(
            new_password
        )

        # 5. Cambiar contraseña mediante el dominio
        user.change_password(new_hashed_password)

        # 6. Persistir
        await self._user_repository.update(user)

        return user_to_dto(user)