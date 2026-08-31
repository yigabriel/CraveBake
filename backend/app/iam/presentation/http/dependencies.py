"""
Composition root for the IAM module.

FastAPI's `Depends` graph is where abstractions get wired to concrete
implementations — this is the only place that imports both the domain
interfaces and their infrastructure implementations, and it is where
Dependency Inversion is actually resolved at runtime.
"""
from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.iam.application.dto.user_dto import UserDTO
from app.iam.application.use_cases.authenticate_user_use_case import AuthenticateUserUseCase
from app.iam.application.use_cases.get_current_user_use_case import GetCurrentUserUseCase
from app.iam.application.use_cases.register_user_use_case import RegisterUserUseCase
from app.iam.application.use_cases.update_unit_preference_use_case import (
    UpdateUnitPreferenceUseCase,
)
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.services.password_hasher import PasswordHasher
from app.iam.domain.services.token_service import TokenService
from app.iam.infraestructure.persistence.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from app.iam.infraestructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.iam.infraestructure.security.jwt_token_service import JwtTokenService
from app.shared.config.settings import get_settings
from app.shared.database.session import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_repository(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_password_hasher() -> PasswordHasher:
    return BcryptPasswordHasher()


def get_token_service() -> TokenService:
    settings = get_settings()
    return JwtTokenService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.access_token_expire_minutes,
    )


def get_register_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> RegisterUserUseCase:
    return RegisterUserUseCase(user_repository, password_hasher)


def get_authenticate_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    token_service: TokenService = Depends(get_token_service),
) -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase(user_repository, password_hasher, token_service)


def get_current_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    token_service: TokenService = Depends(get_token_service),
) -> GetCurrentUserUseCase:
    return GetCurrentUserUseCase(user_repository, token_service)


def get_update_unit_preference_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UpdateUnitPreferenceUseCase:
    return UpdateUnitPreferenceUseCase(user_repository)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    use_case: GetCurrentUserUseCase = Depends(get_current_user_use_case),
) -> UserDTO:
    return await use_case.execute(token)
