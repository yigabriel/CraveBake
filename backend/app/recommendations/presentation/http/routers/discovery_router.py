"""
"¿Qué quiero cocinar?" — Tinder-style recipe discovery.

1. `POST /recommendations/sessions` with the ingredients to cook with (or
   none, to use the pantry) and optional filters (category, tags) starts a
   session.
2. `GET .../deck` returns the best matching recipes — public ones and the
   user's own, their personalization replacing the original — with what
   matches and what is missing.
3. `POST .../swipes` discards, saves (also adds to favorites) or selects a
   recipe. Swiped recipes leave this session's deck only.

Every endpoint requires authentication; sessions are private to their user.
"""
from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.recommendations.application.dto.recommendation_dto import StartSessionDTO
from app.recommendations.application.use_cases.deck_use_cases import (
    GetRecommendationDeckUseCase,
    SwipeRecipeUseCase,
)
from app.recommendations.application.use_cases.session_use_cases import (
    GetDiscoverySessionUseCase,
    ListSwipesUseCase,
    StartDiscoverySessionUseCase,
)
from app.recommendations.presentation.http.dependencies import (
    get_get_discovery_session_use_case,
    get_list_swipes_use_case,
    get_recommendation_deck_use_case,
    get_start_discovery_session_use_case,
    get_swipe_recipe_use_case,
)
from app.recommendations.presentation.http.schemas.recommendation_schemas import (
    DiscoverySessionResponse,
    RecommendationResponse,
    StartSessionRequest,
    SwipeActionLiteral,
    SwipeRequest,
    SwipeResponse,
)
from app.shared.presentation.pagination import PageResponse
from app.shared.presentation.i18n import language_context

router = APIRouter(prefix="/recommendations/sessions", tags=["Recommendations"])


@router.post("", response_model=DiscoverySessionResponse, status_code=status.HTTP_201_CREATED)
async def start_discovery_session(
    request: StartSessionRequest,
    http_request: Request,
    response: Response,
    current_user: UserDTO = Depends(get_current_user),
    use_case: StartDiscoverySessionUseCase = Depends(get_start_discovery_session_use_case),
) -> DiscoverySessionResponse:
    dto = StartSessionDTO(
        user_id=current_user.id,
        ingredient_ids=request.ingredient_ids,
        min_score=request.min_score,
        category_id=request.category_id,
        tag_ids=request.tag_ids,
    )
    session = await use_case.execute(dto)
    response.headers["Location"] = str(http_request.url_for("get_discovery_session", session_id=session.id))
    return DiscoverySessionResponse.model_validate(session, from_attributes=True, context=language_context(current_user))


@router.get("/{session_id}", response_model=DiscoverySessionResponse)
async def get_discovery_session(
    session_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetDiscoverySessionUseCase = Depends(get_get_discovery_session_use_case),
) -> DiscoverySessionResponse:
    session = await use_case.execute(current_user.id, session_id)
    return DiscoverySessionResponse.model_validate(session, from_attributes=True, context=language_context(current_user))


@router.get("/{session_id}/deck", response_model=PageResponse[RecommendationResponse])
async def get_recommendation_deck(
    session_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetRecommendationDeckUseCase = Depends(get_recommendation_deck_use_case),
) -> PageResponse[RecommendationResponse]:
    page = await use_case.execute(current_user.id, session_id, limit=limit, offset=offset)
    return PageResponse[RecommendationResponse].model_validate(page, from_attributes=True, context=language_context(current_user))


@router.post("/{session_id}/swipes", response_model=SwipeResponse, status_code=status.HTTP_201_CREATED)
async def swipe_recipe(
    session_id: str,
    request: SwipeRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: SwipeRecipeUseCase = Depends(get_swipe_recipe_use_case),
) -> SwipeResponse:
    swipe = await use_case.execute(current_user.id, session_id, request.recipe_id, request.action)
    return SwipeResponse(**swipe.__dict__)


@router.get("/{session_id}/swipes", response_model=PageResponse[SwipeResponse])
async def list_session_swipes(
    session_id: str,
    action: SwipeActionLiteral | None = Query(default=None, description="Only swipes of this kind"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListSwipesUseCase = Depends(get_list_swipes_use_case),
) -> PageResponse[SwipeResponse]:
    page = await use_case.execute(current_user.id, session_id, action=action, limit=limit, offset=offset)
    return PageResponse[SwipeResponse].model_validate(page, from_attributes=True, context=language_context(current_user))
