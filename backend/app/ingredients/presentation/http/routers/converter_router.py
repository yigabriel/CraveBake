"""Measurement converter. Requires authentication."""

from fastapi import APIRouter, Depends

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user

from app.ingredients.application.dto.convert_measurement_dto import (
    ConvertMeasurementDTO,
)
from app.ingredients.application.use_cases.convert_measurement_use_case import (
    ConvertMeasurementUseCase,
)
from app.ingredients.presentation.http.dependencies import (
    get_convert_measurement_use_case,
)
from app.ingredients.presentation.http.schemas.converter_schemas import (
    ConvertMeasurementRequest,
    ConvertMeasurementResponse,
)
from app.shared.presentation.i18n import language_context


router = APIRouter(prefix="/converter", tags=["Converter"])


@router.post("", response_model=ConvertMeasurementResponse)
async def convert_measurement(
    request: ConvertMeasurementRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: ConvertMeasurementUseCase = Depends(
        get_convert_measurement_use_case
    ),
) -> ConvertMeasurementResponse:

    dto = ConvertMeasurementDTO(
        quantity=request.quantity,
        from_unit_id=request.from_unit_id,
        to_unit_id=request.to_unit_id,
        ingredient_id=request.ingredient_id,
    )

    result = await use_case.execute(dto)

    return ConvertMeasurementResponse.model_validate(
        result,
        from_attributes=True,
        context=language_context(current_user),
    )