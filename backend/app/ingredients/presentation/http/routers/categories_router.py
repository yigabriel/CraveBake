"""
Ingredient categories.

Requires authentication to access category information.
There is no `Category` entity — `default_category` is free text on
`Ingredient` (see `IngredientRepository.list_distinct_categories`
docstring). This router exposes what's actually in use, and reuses
`SearchIngredientsUseCase` for the "ingredients in this category" listing
instead of duplicating that query.
"""

from fastapi import APIRouter, Depends, Query

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user

from app.ingredients.application.dto.ingredient_dto import SearchIngredientsDTO
from app.ingredients.application.use_cases.list_categories_use_case import (
    ListCategoriesUseCase,
)
from app.ingredients.application.use_cases.search_ingredients_use_case import (
    SearchIngredientsUseCase,
)
from app.ingredients.presentation.http.dependencies import (
    get_list_categories_use_case,
    get_search_ingredients_use_case,
)
from app.ingredients.presentation.http.schemas.category_schemas import (
    CategoryResponse,
)
from app.ingredients.presentation.http.schemas.ingredient_schemas import (
    IngredientResponse,
)
from app.shared.presentation.pagination import PageResponse


router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListCategoriesUseCase = Depends(get_list_categories_use_case),
) -> list[CategoryResponse]:
    categories = await use_case.execute()

    return [
        CategoryResponse(**category.__dict__)
        for category in categories
    ]


@router.get(
    "/{category}/ingredients",
    response_model=PageResponse[IngredientResponse],
)
async def list_ingredients_by_category(
    category: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: SearchIngredientsUseCase = Depends(
        get_search_ingredients_use_case
    ),
) -> PageResponse[IngredientResponse]:

    dto = SearchIngredientsDTO(
        query=None,
        category=category,
        limit=limit,
        offset=offset,
    )

    page = await use_case.execute(dto)

    return PageResponse[IngredientResponse].model_validate(page, from_attributes=True)