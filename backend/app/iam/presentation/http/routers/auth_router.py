"""
Auth endpoints: register and login.

Routers stay thin — they only translate HTTP <-> DTOs and call a use case.
No business rule lives here; that belongs to Domain/Application.
"""
from fastapi import APIRouter, Depends, status

from app.modules.iam.application.dto.login_dto import LoginDTO
from app.modules.iam.application.dto.register_user_dto import RegisterUserDTO
from app.modules.iam.application.use_cases.authenticate_user_use_case import AuthenticateUserUseCase
from app.modules.iam.application.use_cases.register_user_use_case import RegisterUserUseCase
from app.modules.iam.presentation.http.dependencies import (
    get_authenticate_user_use_case,
    get_register_user_use_case,
)
from app.modules.iam.presentation.http.schemas.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.iam.presentation.http.schemas.user_schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    use_case: RegisterUserUseCase = Depends(get_register_user_use_case),
) -> UserResponse:
    dto = RegisterUserDTO(email=request.email, password=request.password, full_name=request.full_name)
    user = await use_case.execute(dto)
    return UserResponse(**user.__dict__)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    use_case: AuthenticateUserUseCase = Depends(get_authenticate_user_use_case),
) -> TokenResponse:
    dto = LoginDTO(email=request.email, password=request.password)
    result = await use_case.execute(dto)
    return TokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user=UserResponse(**result.user.__dict__),
    )
