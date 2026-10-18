"""
"Mi Portafolio": the unified view of the user's original, personalized and saved
recipes, plus favorites management. Every endpoint requires authentication
and only touches the current user's portfolio.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query, status

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.portfolio.application.dto.portfolio_dto import GetPortfolioDTO
from app.portfolio.application.use_cases.favorite_use_cases import (
    GetFavoriteStatusUseCase,
    SaveRecipeUseCase,
    UnsaveRecipeUseCase,
)
from app.portfolio.application.use_cases.get_portfolio_summary_use_case import GetPortfolioSummaryUseCase
from app.portfolio.application.use_cases.get_portfolio_use_case import GetPortfolioUseCase
from app.portfolio.presentation.http.dependencies import (
    get_favorite_status_use_case,
    get_get_portfolio_summary_use_case,
    get_get_portfolio_use_case,
    get_save_recipe_use_case,
    get_unsave_recipe_use_case,
)
from app.portfolio.presentation.http.schemas.portfolio_schemas import (
    FavoriteStatusResponse,
    PortfolioItemResponse,
    PortfolioSummaryResponse,
)
from app.shared.presentation.pagination import PageResponse

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("", response_model=PageResponse[PortfolioItemResponse])
async def get_my_portfolio(
    kind: Literal["original", "personalized", "saved"] | None = Query(
        default=None, description="Only one section; everything when omitted"
    ),
    q: str | None = Query(default=None, description="Text to look for in the recipe title"),
    category_id: str | None = Query(default=None, description="Only recipes of this category"),
    tag_ids: list[str] = Query(default=[], description="Recipe must have all of these tags"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetPortfolioUseCase = Depends(get_get_portfolio_use_case),
) -> PageResponse[PortfolioItemResponse]:
    dto = GetPortfolioDTO(
        user_id=current_user.id,
        kind=kind,
        query=q,
        category_id=category_id,
        tag_ids=tag_ids,
        limit=limit,
        offset=offset,
    )
    page = await use_case.execute(dto)
    return PageResponse[PortfolioItemResponse].model_validate(page, from_attributes=True)


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_my_portfolio_summary(
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetPortfolioSummaryUseCase = Depends(get_get_portfolio_summary_use_case),
) -> PortfolioSummaryResponse:
    summary = await use_case.execute(current_user.id)
    return PortfolioSummaryResponse(**summary.__dict__)


@router.get("/favorites", response_model=PageResponse[PortfolioItemResponse])
async def list_my_favorites(
    q: str | None = Query(default=None, description="Text to look for in the recipe title"),
    category_id: str | None = Query(default=None, description="Only recipes of this category"),
    tag_ids: list[str] = Query(default=[], description="Recipe must have all of these tags"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetPortfolioUseCase = Depends(get_get_portfolio_use_case),
) -> PageResponse[PortfolioItemResponse]:
    dto = GetPortfolioDTO(
        user_id=current_user.id,
        kind="saved",
        query=q,
        category_id=category_id,
        tag_ids=tag_ids,
        limit=limit,
        offset=offset,
    )
    page = await use_case.execute(dto)
    return PageResponse[PortfolioItemResponse].model_validate(page, from_attributes=True)


@router.get("/favorites/status", response_model=list[FavoriteStatusResponse])
async def get_favorites_status(
    recipe_ids: list[str] = Query(description="Recipe ids to check, e.g. ?recipe_ids=a&recipe_ids=b"),
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetFavoriteStatusUseCase = Depends(get_favorite_status_use_case),
) -> list[FavoriteStatusResponse]:
    statuses = await use_case.execute(current_user.id, recipe_ids)
    return [FavoriteStatusResponse(**item.__dict__) for item in statuses]


@router.put("/favorites/{recipe_id}", response_model=PortfolioItemResponse)
async def save_recipe(
    recipe_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: SaveRecipeUseCase = Depends(get_save_recipe_use_case),
) -> PortfolioItemResponse:
    item = await use_case.execute(current_user.id, recipe_id)
    return PortfolioItemResponse(**item.__dict__)


@router.delete("/favorites/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_recipe(
    recipe_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: UnsaveRecipeUseCase = Depends(get_unsave_recipe_use_case),
) -> None:
    await use_case.execute(current_user.id, recipe_id)
