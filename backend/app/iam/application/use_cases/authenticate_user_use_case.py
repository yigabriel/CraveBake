"""
AuthenticateUserUseCase.

Verifies credentials and issues an access token. 
Password comparison is delegated to `PasswordHasher.verify`.
token issuance is delegated to `TokenService`. 
The use case itself has no idea whether passwords arehashed with bcrypt or tokens are JWTs.
"""
from __future__ import annotations # facilita el uso de type hints / No intentar resolver los tipos ahora, déjalos para después

from app.iam.application.dto.auth_result_dto import AuthResultDTO
from app.iam.application.dto.login_dto import LoginDTO
from app.iam.application.mappers.user_mapper import user_to_dto
from app.iam.domain.exceptions import InactiveUserError, InvalidCredentialsError
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.services.password_hasher import PasswordHasher
from app.iam.domain.services.token_service import TokenService
from app.iam.domain.value_objects.email import Email


class AuthenticateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service

    async def execute(self, dto: LoginDTO) -> AuthResultDTO:
        email = Email(dto.email)
        user = await self._user_repository.get_by_email(email)

        if user is None or not self._password_hasher.verify(dto.password, user.hashed_password):
            # Same error for "no such email" and "wrong password" on purpose:
            raise InvalidCredentialsError()

        if not user.is_active:
            # user marked as inactive
            raise InactiveUserError()

        access_token = self._token_service.generate_access_token(user.id)

        return AuthResultDTO(access_token=access_token, token_type="bearer", user=user_to_dto(user))
