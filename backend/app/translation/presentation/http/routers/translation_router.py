"""
Translation suggestions for catalog names.

Used when a user adds an ingredient or equipment: the app suggests how it
reads in the other languages, the user checks it, and only then is it saved.
"""
from fastapi import APIRouter, Depends

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.translation.application.dto.translation_dto import SuggestTranslationsDTO
from app.translation.application.use_cases.suggest_translations_use_case import SuggestTranslationsUseCase
from app.translation.infrastructure.request_rate_limiter import RequestRateLimiter
from app.translation.presentation.http.dependencies import (
    get_suggest_translations_use_case,
    get_translation_rate_limiter,
)
from app.translation.presentation.http.schemas.translation_schemas import (
    SuggestTranslationsRequest,
    SuggestTranslationsResponse,
)

router = APIRouter(prefix="/translations", tags=["Translations"])


@router.post("", response_model=SuggestTranslationsResponse)
async def suggest_translations(
    request: SuggestTranslationsRequest,
    current_user: UserDTO = Depends(get_current_user),
    limiter: RequestRateLimiter = Depends(get_translation_rate_limiter),
    use_case: SuggestTranslationsUseCase = Depends(get_suggest_translations_use_case),
) -> SuggestTranslationsResponse:
    limiter.hit(current_user.id)
    translations = await use_case.execute(SuggestTranslationsDTO(text=request.text, source=request.source))
    return SuggestTranslationsResponse(translations=translations)
