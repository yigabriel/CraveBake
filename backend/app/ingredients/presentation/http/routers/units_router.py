"""Reference catalog of measurement units. Requires authentication."""

from fastapi import APIRouter, Depends

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user

from app.ingredients.application.use_cases.list_units_use_case import (
    ListUnitsUseCase,
)
from app.ingredients.presentation.http.dependencies import (
    get_list_units_use_case,
)
from app.ingredients.presentation.http.schemas.unit_schemas import UnitResponse
from app.shared.presentation.i18n import language_context


router = APIRouter(prefix="/units", tags=["Units"])


@router.get("", response_model=list[UnitResponse])
async def list_units(
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListUnitsUseCase = Depends(get_list_units_use_case),
) -> list[UnitResponse]:

    units = await use_case.execute()

    return [
        UnitResponse.model_validate(unit, from_attributes=True, context=language_context(current_user))
        for unit in units
    ]