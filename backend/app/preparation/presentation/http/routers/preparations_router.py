"""
Guided cooking mode ("modo preparación") and cooking history.

- `POST /preparations` starts cooking a recipe, or resumes the preparation of
  that recipe already in progress (201 when new, 200 when resumed).
- The step endpoints drive the guided mode; each returns the full updated
  preparation, so the client re-renders from one response.
- Quantities are shown in the user's preferred unit system (profile), or in
  the one asked with `?unit_system=metric|us|original`.

Every endpoint requires authentication; preparations are private to their user.
"""
from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.preparation.application.use_cases.preparation_use_cases import (
    GetPreparationUseCase,
    ListPreparationsUseCase,
    PreparationProgressUseCases,
    StartPreparationUseCase,
)
from app.preparation.presentation.http.dependencies import (
    get_get_preparation_use_case,
    get_list_preparations_use_case,
    get_preparation_progress_use_cases,
    get_start_preparation_use_case,
)
from app.preparation.presentation.http.schemas.preparation_schemas import (
    GoToStepRequest,
    PreparationDetailResponse,
    PreparationStatusLiteral,
    PreparationSummaryResponse,
    StartPreparationRequest,
    UnitSystemLiteral,
)
from app.shared.presentation.pagination import PageResponse
from app.shared.presentation.i18n import language_context

router = APIRouter(prefix="/preparations", tags=["Preparations"])

_UNIT_SYSTEM_QUERY = Query(
    default=None, description="metric | us | original. Defaults to the user's preferred unit system"
)


def _unit_system(requested: str | None, user: UserDTO) -> str:
    return requested or user.preferred_unit_system


def _detail(preparation, user: UserDTO) -> PreparationDetailResponse:
    return PreparationDetailResponse.model_validate(preparation, from_attributes=True, context=language_context(user))


@router.post(
    "",
    response_model=PreparationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "A preparation of this recipe was already in progress and is resumed"}},
)
async def start_preparation(
    request: StartPreparationRequest,
    http_request: Request,
    response: Response,
    unit_system: UnitSystemLiteral | None = _UNIT_SYSTEM_QUERY,
    current_user: UserDTO = Depends(get_current_user),
    use_case: StartPreparationUseCase = Depends(get_start_preparation_use_case),
) -> PreparationDetailResponse:
    started = await use_case.execute(current_user.id, request.recipe_id, _unit_system(unit_system, current_user))
    if started.resumed:
        response.status_code = status.HTTP_200_OK
    response.headers["Location"] = str(
        http_request.url_for("get_preparation", preparation_id=started.preparation.id)
    )
    return _detail(started.preparation, current_user)


@router.get("", response_model=PageResponse[PreparationSummaryResponse])
async def list_my_preparations(
    status_filter: PreparationStatusLiteral | None = Query(default=None, alias="status"),
    recipe_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListPreparationsUseCase = Depends(get_list_preparations_use_case),
) -> PageResponse[PreparationSummaryResponse]:
    page = await use_case.execute(current_user.id, status_filter, recipe_id, limit, offset)
    return PageResponse[PreparationSummaryResponse].model_validate(page, from_attributes=True, context=language_context(current_user))


@router.get("/{preparation_id}", response_model=PreparationDetailResponse)
async def get_preparation(
    preparation_id: str,
    unit_system: UnitSystemLiteral | None = _UNIT_SYSTEM_QUERY,
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetPreparationUseCase = Depends(get_get_preparation_use_case),
) -> PreparationDetailResponse:
    return _detail(await use_case.execute(current_user.id, preparation_id, _unit_system(unit_system, current_user)), current_user)


@router.put("/{preparation_id}/current-step", response_model=PreparationDetailResponse)
async def go_to_step(
    preparation_id: str,
    request: GoToStepRequest,
    unit_system: UnitSystemLiteral | None = _UNIT_SYSTEM_QUERY,
    current_user: UserDTO = Depends(get_current_user),
    use_cases: PreparationProgressUseCases = Depends(get_preparation_progress_use_cases),
) -> PreparationDetailResponse:
    return _detail(
        await use_cases.go_to_step(
            current_user.id, preparation_id, request.step_number, _unit_system(unit_system, current_user)
        ),
        current_user,
    )


@router.post("/{preparation_id}/steps/{step_number}/complete", response_model=PreparationDetailResponse)
async def complete_step(
    preparation_id: str,
    step_number: int,
    unit_system: UnitSystemLiteral | None = _UNIT_SYSTEM_QUERY,
    current_user: UserDTO = Depends(get_current_user),
    use_cases: PreparationProgressUseCases = Depends(get_preparation_progress_use_cases),
) -> PreparationDetailResponse:
    return _detail(
        await use_cases.complete_step(current_user.id, preparation_id, step_number, _unit_system(unit_system, current_user)),
        current_user,
    )


@router.delete("/{preparation_id}/steps/{step_number}/complete", response_model=PreparationDetailResponse)
async def uncomplete_step(
    preparation_id: str,
    step_number: int,
    unit_system: UnitSystemLiteral | None = _UNIT_SYSTEM_QUERY,
    current_user: UserDTO = Depends(get_current_user),
    use_cases: PreparationProgressUseCases = Depends(get_preparation_progress_use_cases),
) -> PreparationDetailResponse:
    return _detail(
        await use_cases.uncomplete_step(
            current_user.id, preparation_id, step_number, _unit_system(unit_system, current_user)
        ),
        current_user,
    )


@router.post("/{preparation_id}/steps/{step_number}/timer", response_model=PreparationDetailResponse)
async def start_step_timer(
    preparation_id: str,
    step_number: int,
    unit_system: UnitSystemLiteral | None = _UNIT_SYSTEM_QUERY,
    current_user: UserDTO = Depends(get_current_user),
    use_cases: PreparationProgressUseCases = Depends(get_preparation_progress_use_cases),
) -> PreparationDetailResponse:
    return _detail(
        await use_cases.start_timer(current_user.id, preparation_id, step_number, _unit_system(unit_system, current_user)),
        current_user,
    )


@router.post("/{preparation_id}/finish", response_model=PreparationDetailResponse)
async def finish_preparation(
    preparation_id: str,
    unit_system: UnitSystemLiteral | None = _UNIT_SYSTEM_QUERY,
    current_user: UserDTO = Depends(get_current_user),
    use_cases: PreparationProgressUseCases = Depends(get_preparation_progress_use_cases),
) -> PreparationDetailResponse:
    return _detail(await use_cases.finish(current_user.id, preparation_id, _unit_system(unit_system, current_user)), current_user)


@router.post("/{preparation_id}/abandon", response_model=PreparationDetailResponse)
async def abandon_preparation(
    preparation_id: str,
    unit_system: UnitSystemLiteral | None = _UNIT_SYSTEM_QUERY,
    current_user: UserDTO = Depends(get_current_user),
    use_cases: PreparationProgressUseCases = Depends(get_preparation_progress_use_cases),
) -> PreparationDetailResponse:
    return _detail(await use_cases.abandon(current_user.id, preparation_id, _unit_system(unit_system, current_user)), current_user)
