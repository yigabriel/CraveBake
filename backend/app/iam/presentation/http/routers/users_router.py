
"""Endpoints about the authenticated user's own profile."""

from fastapi import APIRouter, Depends

from app.iam.application.dto.change_password_dto import ChangePasswordDTO
from app.iam.application.dto.update_language_dto import UpdateLanguageDTO
from app.iam.application.dto.update_user_dto import UpdateUserDTO
from app.iam.application.dto.update_unit_preference_dto import UpdateUnitPreferenceDTO
from app.iam.application.dto.user_dto import UserDTO

from app.iam.application.use_cases.change_password_use_case import (
    ChangePasswordUseCase,
)
from app.iam.application.use_cases.update_language_use_case import (
    UpdateLanguageUseCase,
)
from app.iam.application.use_cases.update_profile_use_case import (
    UpdateProfileUseCase,
)
from app.iam.application.use_cases.update_unit_preference_use_case import (
    UpdateUnitPreferenceUseCase,
)
from app.iam.presentation.http.dependencies import (
    get_change_password_use_case,
    get_current_user,
    get_update_language_use_case,
    get_update_profile_use_case,
    get_update_unit_preference_use_case,
)

from app.iam.presentation.http.schemas.user_schemas import (
    ChangePasswordRequest,
    UpdateLanguageRequest,
    UpdateProfileRequest,
    UpdateUnitPreferenceRequest,
    UserResponse,
)


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: UserDTO = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(**current_user.__dict__)


@router.patch("/me/unit-preference", response_model=UserResponse)
async def update_my_unit_preference(
    request: UpdateUnitPreferenceRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: UpdateUnitPreferenceUseCase = Depends(
        get_update_unit_preference_use_case
    ),
) -> UserResponse:

    dto = UpdateUnitPreferenceDTO(
        preferred_unit_system=request.preferred_unit_system,
    )

    updated_user = await use_case.execute(current_user.id, dto)

    return UserResponse(**updated_user.__dict__)

@router.patch("/me/language", response_model=UserResponse)
async def update_my_language(
    request: UpdateLanguageRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: UpdateLanguageUseCase = Depends(
        get_update_language_use_case
    ),
) -> UserResponse:

    dto = UpdateLanguageDTO(
        preferred_language=request.preferred_language,
    )

    updated_user = await use_case.execute(current_user.id, dto)

    return UserResponse(**updated_user.__dict__)

@router.patch("/me/profile", response_model=UserResponse)
async def update_my_profile(
    request: UpdateProfileRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: UpdateProfileUseCase = Depends(
        get_update_profile_use_case
    ),
) -> UserResponse:

    dto = UpdateUserDTO(
        full_name=request.full_name,
        avatar_url=request.avatar_url,
    )

    updated_user = await use_case.execute(current_user.id, dto)

    return UserResponse(**updated_user.__dict__)


@router.patch("/me/change-password", response_model=UserResponse)
async def change_my_password(
    request: ChangePasswordRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: ChangePasswordUseCase = Depends(
        get_change_password_use_case
    ),
) -> UserResponse:

    dto = ChangePasswordDTO(
        current_password=request.current_password,
        new_password=request.new_password,
    )

    updated_user = await use_case.execute(current_user.id, dto)

    return UserResponse(**updated_user.__dict__)
