from __future__ import annotations

from app.iam.application.dto.change_password_dto import ChangePasswordDTO
from app.iam.application.dto.user_dto import UserDTO
from app.iam.application.mappers.user_mapper import user_to_dto
from app.iam.domain.exceptions import (
    IncorrectCurrentPasswordError,
    UserNotFoundError,
)
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.services.password_hasher import PasswordHasher
from app.iam.domain.value_objects.plain_password import PlainPassword
from app.iam.domain.value_objects.user_id import UserId


class ChangePasswordUseCase:

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher

    async def execute(
        self,
        user_id: str,
        dto: ChangePasswordDTO,
    ) -> UserDTO:

        # 1. Obtener el usuario autenticado
        user = await self._user_repository.get_by_id(UserId.from_string(user_id))
        if user is None:
            raise UserNotFoundError(user_id)

        # 2. Verificar la contraseña actual. No se envuelve en PlainPassword:
        #    la actual pudo crearse antes de las reglas de fuerza vigentes.
        if not self._password_hasher.verify(
            dto.current_password,
            user.hashed_password,
        ):
            raise IncorrectCurrentPasswordError()

        # 3. Validar la nueva contraseña con las reglas del dominio y hashearla
        new_hashed_password = self._password_hasher.hash(
            PlainPassword(dto.new_password)
        )

        # 4. Cambiar contraseña mediante el dominio
        user.change_password(new_hashed_password)

        # 5. Persistir
        await self._user_repository.update(user)

        return user_to_dto(user)
