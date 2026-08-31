"""Endpoints about the authenticated user's own profile."""
from fastapi import APIRouter, Depends

from app.modules.iam.application.dto.update_unit_preference_dto import UpdateUnitPreferenceDTO
from app.modules.iam.application.dto.user_dto import UserDTO
from app.modules.iam.application.use_cases.update_unit_preference_use_case import (
    UpdateUnitPreferenceUseCase,
)
from app.modules.iam.presentation.http.dependencies import (
    get_current_user,
    get_update_unit_preference_use_case,
)
from app.modules.iam.presentation.http.schemas.user_schemas import (
    UpdateUnitPreferenceRequest,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserDTO = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**current_user.__dict__)


@router.patch("/me/unit-preference", response_model=UserResponse)
async def update_my_unit_preference(
    request: UpdateUnitPreferenceRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: UpdateUnitPreferenceUseCase = Depends(get_update_unit_preference_use_case),
) -> UserResponse:
    dto = UpdateUnitPreferenceDTO(
        user_id=current_user.id,
        preferred_unit_system=request.preferred_unit_system,
    )
    updated_user = await use_case.execute(dto)
    return UserResponse(**updated_user.__dict__)
