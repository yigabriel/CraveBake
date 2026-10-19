"""
The authenticated user's pantry ("ingredientes disponibles" en su perfil).

Every endpoint requires authentication and only accesses the current
user's own pantry rows.
"""

from fastapi import APIRouter, Depends, status
from app.shared.presentation.i18n import language_context

from app.iam.application.dto.user_dto import UserDTO
from app.ingredients.application.dto.user_ingredient_dto import (
    UpsertUserIngredientDTO,
)
from app.ingredients.application.use_cases.list_user_ingredients_use_case import (
    ListUserIngredientsUseCase,
)
from app.ingredients.application.use_cases.remove_user_ingredient_use_case import (
    RemoveUserIngredientUseCase,
)
from app.ingredients.application.use_cases.upsert_user_ingredient_use_case import (
    UpsertUserIngredientUseCase,
)
from app.ingredients.presentation.http.dependencies import (
    get_current_user,
    get_list_user_ingredients_use_case,
    get_remove_user_ingredient_use_case,
    get_upsert_user_ingredient_use_case,
)
from app.ingredients.presentation.http.schemas.user_ingredient_schemas import (
    UpsertUserIngredientRequest,
    UserIngredientResponse,
)


router = APIRouter(prefix="/pantry", tags=["Pantry"])


@router.get("", response_model=list[UserIngredientResponse])
async def list_my_pantry(
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListUserIngredientsUseCase = Depends(
        get_list_user_ingredients_use_case
    ),
) -> list[UserIngredientResponse]:

    pantry_items = await use_case.execute(current_user.id)

    return [
        UserIngredientResponse.model_validate(
            item,
            from_attributes=True,
            context=language_context(current_user),
        )
        for item in pantry_items
    ]


@router.put("", response_model=UserIngredientResponse)
async def upsert_pantry_item(
    request: UpsertUserIngredientRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: UpsertUserIngredientUseCase = Depends(
        get_upsert_user_ingredient_use_case
    ),
) -> UserIngredientResponse:

    dto = UpsertUserIngredientDTO(
        user_id=current_user.id,
        ingredient_id=request.ingredient_id,
        quantity=request.quantity,
        unit_id=request.unit_id,
    )

    pantry_item = await use_case.execute(dto)

    return UserIngredientResponse.model_validate(
        pantry_item,
        from_attributes=True,
        context=language_context(current_user),
    )


@router.delete(
    "/{ingredient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_pantry_item(
    ingredient_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: RemoveUserIngredientUseCase = Depends(
        get_remove_user_ingredient_use_case
    ),
) -> None:

    await use_case.execute(
        current_user.id,
        ingredient_id,
    )