from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.iam.application.dto.login_dto import LoginDTO
from app.iam.application.dto.register_user_dto import RegisterUserDTO
from app.iam.application.use_cases.authenticate_user_use_case import AuthenticateUserUseCase
from app.iam.application.use_cases.register_user_use_case import RegisterUserUseCase
from app.iam.domain.exceptions import InvalidCredentialsError
from app.iam.infraestructure.security.login_rate_limiter import LoginRateLimiter
from app.iam.presentation.http.dependencies import (
    get_authenticate_user_use_case,
    get_login_rate_limiter,
    get_register_user_use_case,
)
from app.iam.presentation.http.schemas.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.iam.presentation.http.schemas.user_schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    use_case: RegisterUserUseCase = Depends(get_register_user_use_case),
) -> UserResponse:
    dto = RegisterUserDTO(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )

    user = await use_case.execute(dto)

    return UserResponse(**user.__dict__)


@router.post("/login", response_model=TokenResponse)
async def login(
    http_request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    use_case: AuthenticateUserUseCase = Depends(get_authenticate_user_use_case),
    rate_limiter: LoginRateLimiter = Depends(get_login_rate_limiter),
) -> TokenResponse:
    # Keyed by IP + email so an attacker cannot lock a victim out from elsewhere.
    # Behind a reverse proxy, run uvicorn with --proxy-headers so this is the real client IP.
    client_ip = http_request.client.host if http_request.client else "unknown"
    rate_limit_key = f"{client_ip}:{form_data.username.strip().lower()}"
    rate_limiter.ensure_allowed(rate_limit_key)

    dto = LoginDTO(
        email=form_data.username,
        password=form_data.password,
    )

    try:
        result = await use_case.execute(dto)
    except InvalidCredentialsError:
        rate_limiter.register_failure(rate_limit_key)
        raise

    rate_limiter.reset(rate_limit_key)

    return TokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user=UserResponse(**result.user.__dict__),
    )