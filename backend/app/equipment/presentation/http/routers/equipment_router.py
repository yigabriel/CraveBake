"""
Equipment: the shared catalog (search, detail, creation) and the user's
kitchen (`/equipment/mine`). Every endpoint requires authentication; the
kitchen endpoints only touch the current user's rows.
"""
from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.equipment.application.dto.equipment_dto import (
    CreateEquipmentDTO,
    SearchEquipmentDTO,
    UpsertUserEquipmentDTO,
)
from app.equipment.application.use_cases.equipment_catalog_use_cases import (
    CreateEquipmentUseCase,
    GetEquipmentUseCase,
    SearchEquipmentUseCase,
)
from app.equipment.application.use_cases.user_equipment_use_cases import (
    ListUserEquipmentUseCase,
    RemoveUserEquipmentUseCase,
    UpsertUserEquipmentUseCase,
)
from app.equipment.presentation.http.dependencies import (
    get_create_equipment_use_case,
    get_get_equipment_use_case,
    get_list_user_equipment_use_case,
    get_remove_user_equipment_use_case,
    get_search_equipment_use_case,
    get_upsert_user_equipment_use_case,
)
from app.equipment.presentation.http.schemas.equipment_schemas import (
    CreateEquipmentRequest,
    EquipmentResponse,
    EquipmentTypeLiteral,
    UpsertUserEquipmentRequest,
    UserEquipmentResponse,
)
from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.shared.presentation.pagination import PageResponse
from app.shared.presentation.i18n import language_context

router = APIRouter(prefix="/equipment", tags=["Equipment"])


@router.get("", response_model=PageResponse[EquipmentResponse])
async def search_equipment(
    q: str | None = Query(default=None, description="Text to look for in the equipment name"),
    equipment_type: EquipmentTypeLiteral | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: SearchEquipmentUseCase = Depends(get_search_equipment_use_case),
) -> PageResponse[EquipmentResponse]:
    dto = SearchEquipmentDTO(query=q, equipment_type=equipment_type, limit=limit, offset=offset)
    page = await use_case.execute(dto)
    return PageResponse[EquipmentResponse].model_validate(page, from_attributes=True, context=language_context(current_user))


@router.post("", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    request: CreateEquipmentRequest,
    http_request: Request,
    response: Response,
    current_user: UserDTO = Depends(get_current_user),
    use_case: CreateEquipmentUseCase = Depends(get_create_equipment_use_case),
) -> EquipmentResponse:
    dto = CreateEquipmentDTO(
        name=request.name,
        equipment_type=request.equipment_type,
        description=request.description,
        # The name is taken as written in the creator's language.
        language=current_user.preferred_language,
    )
    equipment = await use_case.execute(dto)
    response.headers["Location"] = str(http_request.url_for("get_equipment", equipment_id=equipment.id))
    return EquipmentResponse.model_validate(equipment, from_attributes=True, context=language_context(current_user))


# --- The user's kitchen (declared before /{equipment_id} so "mine" is not taken as an id)


@router.get("/mine", response_model=list[UserEquipmentResponse])
async def list_my_equipment(
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListUserEquipmentUseCase = Depends(get_list_user_equipment_use_case),
) -> list[UserEquipmentResponse]:
    items = await use_case.execute(current_user.id)
    return [UserEquipmentResponse.model_validate(item, from_attributes=True, context=language_context(current_user)) for item in items]


@router.put("/mine", response_model=UserEquipmentResponse)
async def upsert_my_equipment(
    request: UpsertUserEquipmentRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: UpsertUserEquipmentUseCase = Depends(get_upsert_user_equipment_use_case),
) -> UserEquipmentResponse:
    dto = UpsertUserEquipmentDTO(
        user_id=current_user.id,
        equipment_id=request.equipment_id,
        quantity=request.quantity,
        notes=request.notes,
    )
    item = await use_case.execute(dto)
    return UserEquipmentResponse.model_validate(item, from_attributes=True, context=language_context(current_user))


@router.delete("/mine/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_my_equipment(
    equipment_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: RemoveUserEquipmentUseCase = Depends(get_remove_user_equipment_use_case),
) -> None:
    await use_case.execute(current_user.id, equipment_id)


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetEquipmentUseCase = Depends(get_get_equipment_use_case),
) -> EquipmentResponse:
    equipment = await use_case.execute(equipment_id)
    return EquipmentResponse.model_validate(equipment, from_attributes=True, context=language_context(current_user))
