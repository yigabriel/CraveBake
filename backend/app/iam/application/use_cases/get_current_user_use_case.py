"""
GetCurrentUserUseCase.

Resolves the authenticated user from a bearer token. 

"""
from __future__ import annotations

from app.iam.application.dto.user_dto import UserDTO
from app.iam.application.mappers.user_mapper import user_to_dto
from app.iam.domain.exceptions import InactiveUserError, InvalidTokenError, UserNotFoundError
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.services.token_service import TokenService


class GetCurrentUserUseCase:
    def __init__(self, user_repository: UserRepository, token_service: TokenService) -> None:
        self._user_repository = user_repository
        self._token_service = token_service

    async def execute(self, access_token: str) -> UserDTO:
        try:
            # Paquete
            #    ├──  Contenedor / envoltorio
            #    └──  Payload → los datos que lleva dentro
            payload = self._token_service.decode_access_token(access_token)
        except Exception as error:
            raise InvalidTokenError() from error

        user = await self._user_repository.get_by_id(payload.user_id)
        if user is None:
            raise UserNotFoundError(str(payload.user_id))
        if not user.is_active:
            raise InactiveUserError()

        return user_to_dto(user)
