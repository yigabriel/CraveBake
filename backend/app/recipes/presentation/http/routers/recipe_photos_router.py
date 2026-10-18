"""
Recipe photos, registered by URL: up to 3 cover photos (carousel) and one
photo per step. Listing follows recipe visibility; changes are owner-only.
"""
from fastapi import APIRouter, Depends, status

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.recipes.application.dto.recipe_dto import AddRecipePhotoDTO
from app.recipes.application.use_cases.recipe_photo_use_cases import (
    AddRecipePhotoUseCase,
    ListRecipePhotosUseCase,
    RemoveRecipePhotoUseCase,
    ReorderCoverPhotosUseCase,
)
from app.recipes.presentation.http.dependencies import (
    get_add_recipe_photo_use_case,
    get_list_recipe_photos_use_case,
    get_remove_recipe_photo_use_case,
    get_reorder_cover_photos_use_case,
)
from app.recipes.presentation.http.schemas.recipe_schemas import (
    AddRecipePhotoRequest,
    RecipePhotoResponse,
    ReorderCoverPhotosRequest,
)

router = APIRouter(prefix="/recipes/{recipe_id}/photos", tags=["Recipe photos"])


@router.get("", response_model=list[RecipePhotoResponse])
async def list_recipe_photos(
    recipe_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListRecipePhotosUseCase = Depends(get_list_recipe_photos_use_case),
) -> list[RecipePhotoResponse]:
    photos = await use_case.execute(current_user.id, recipe_id)
    return [RecipePhotoResponse.model_validate(photo, from_attributes=True) for photo in photos]


@router.post("", response_model=RecipePhotoResponse, status_code=status.HTTP_201_CREATED)
async def add_recipe_photo(
    recipe_id: str,
    request: AddRecipePhotoRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: AddRecipePhotoUseCase = Depends(get_add_recipe_photo_use_case),
) -> RecipePhotoResponse:
    dto = AddRecipePhotoDTO(
        user_id=current_user.id,
        recipe_id=recipe_id,
        photo_type=request.photo_type,
        photo_url=request.photo_url,
        step_id=request.step_id,
    )
    photo = await use_case.execute(dto)
    return RecipePhotoResponse.model_validate(photo, from_attributes=True)


@router.put("/cover-order", response_model=list[RecipePhotoResponse])
async def reorder_cover_photos(
    recipe_id: str,
    request: ReorderCoverPhotosRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: ReorderCoverPhotosUseCase = Depends(get_reorder_cover_photos_use_case),
) -> list[RecipePhotoResponse]:
    photos = await use_case.execute(current_user.id, recipe_id, request.photo_ids)
    return [RecipePhotoResponse.model_validate(photo, from_attributes=True) for photo in photos]


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_recipe_photo(
    recipe_id: str,
    photo_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: RemoveRecipePhotoUseCase = Depends(get_remove_recipe_photo_use_case),
) -> None:
    await use_case.execute(current_user.id, recipe_id, photo_id)
