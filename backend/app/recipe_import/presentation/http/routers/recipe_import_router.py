"""
Recipe import: a TikTok / Instagram Reel link in, a recipe draft out.

Nothing is created here. The draft is reviewed in the recipe editor and saved with the normal
`POST /recipes`, so an imported recipe obeys every rule of a written one.
"""
from fastapi import APIRouter, Depends

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.recipe_import.application.dto.recipe_draft_dto import ImportRecipeDTO
from app.recipe_import.application.use_cases.import_recipe_from_video_use_case import ImportRecipeFromVideoUseCase
from app.recipe_import.domain.source_url import parse_source_url
from app.recipe_import.presentation.http.dependencies import get_import_rate_limiter, get_import_recipe_use_case
from app.recipe_import.presentation.http.schemas.recipe_import_schemas import ImportRecipeRequest, RecipeDraftResponse
from app.shared.presentation.i18n import language_context
from app.shared.presentation.request_rate_limiter import RequestRateLimiter

router = APIRouter(prefix="/recipe-imports", tags=["Recipe import"])


@router.post("", response_model=RecipeDraftResponse)
async def import_recipe_from_video(
    request: ImportRecipeRequest,
    current_user: UserDTO = Depends(get_current_user),
    limiter: RequestRateLimiter = Depends(get_import_rate_limiter),
    use_case: ImportRecipeFromVideoUseCase = Depends(get_import_recipe_use_case),
) -> RecipeDraftResponse:
    parse_source_url(request.url)  # a link that is not ours to import is a 400 that costs nothing
    limiter.hit(current_user.id)  # every import costs provider credits
    draft = await use_case.execute(ImportRecipeDTO(url=request.url))
    return RecipeDraftResponse.model_validate(draft, from_attributes=True, context=language_context(current_user))
