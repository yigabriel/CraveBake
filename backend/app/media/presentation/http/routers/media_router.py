"""
Photo uploads.

The browser asks here for a single-use upload URL, PUTs the (already resized)
photo straight to storage, then registers `public_url` where it belongs:
POST /recipes/{id}/photos or PATCH /users/me/profile (avatar_url).
"""
from fastapi import APIRouter, Depends, status

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.media.application.dto.image_upload_dto import RequestImageUploadDTO
from app.media.application.use_cases.request_image_upload_use_case import RequestImageUploadUseCase
from app.media.presentation.http.dependencies import get_request_image_upload_use_case
from app.media.presentation.http.schemas.media_schemas import ImageUploadResponse, RequestImageUploadRequest

router = APIRouter(prefix="/media", tags=["Media"])


@router.post(
    "/uploads",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={503: {"description": "Image storage is not configured or unreachable"}},
)
async def request_image_upload(
    request: RequestImageUploadRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: RequestImageUploadUseCase = Depends(get_request_image_upload_use_case),
) -> ImageUploadResponse:
    upload = await use_case.execute(
        RequestImageUploadDTO(user_id=current_user.id, purpose=request.purpose, content_type=request.content_type)
    )
    return ImageUploadResponse.model_validate(upload, from_attributes=True)
