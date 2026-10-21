"""
Ingredients catalog: search, detail and creation. Requires authentication.

Any authenticated user can add ingredients (there is no admin role yet);
names are unique, case-insensitively.
"""

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user

from app.ingredients.application.dto.ingredient_dto import (
    CreateIngredientDTO,
    SearchIngredientsDTO,
)
from app.ingredients.application.use_cases.create_ingredient_use_case import (
    CreateIngredientUseCase,
)
from app.ingredients.application.use_cases.get_ingredient_use_case import (
    GetIngredientUseCase,
)
from app.ingredients.application.use_cases.search_ingredients_use_case import (
    SearchIngredientsUseCase,
)
from app.ingredients.presentation.http.dependencies import (
    get_create_ingredient_use_case,
    get_get_ingredient_use_case,
    get_search_ingredients_use_case,
)
from app.ingredients.presentation.http.schemas.ingredient_schemas import (
    CreateIngredientRequest,
    IngredientResponse,
)
from app.shared.presentation.pagination import PageResponse
from app.shared.presentation.i18n import language_context


router = APIRouter(prefix="/ingredients", tags=["Ingredients"])


@router.get("", response_model=PageResponse[IngredientResponse])
async def search_ingredients(
    q: str | None = Query(default=None, description="Text to look for in the ingredient name"),
    category: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: SearchIngredientsUseCase = Depends(
        get_search_ingredients_use_case
    ),
) -> PageResponse[IngredientResponse]:

    dto = SearchIngredientsDTO(
        query=q,
        category=category,
        limit=limit,
        offset=offset,
    )

    page = await use_case.execute(dto)

    return PageResponse[IngredientResponse].model_validate(page, from_attributes=True, context=language_context(current_user))


@router.post(
    "",
    response_model=IngredientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ingredient(
    request: CreateIngredientRequest,
    http_request: Request,
    response: Response,
    current_user: UserDTO = Depends(get_current_user),
    use_case: CreateIngredientUseCase = Depends(
        get_create_ingredient_use_case
    ),
) -> IngredientResponse:

    dto = CreateIngredientDTO(
        name=request.name,
        description=request.description,
        default_category=request.default_category,
        translations=dict(request.translations),
        # The name is taken as written in the creator's language.
        language=current_user.preferred_language,
    )

    ingredient = await use_case.execute(dto)

    response.headers["Location"] = str(http_request.url_for("get_ingredient", ingredient_id=ingredient.id))
    return IngredientResponse.model_validate(ingredient, from_attributes=True, context=language_context(current_user))


@router.get("/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(
    ingredient_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetIngredientUseCase = Depends(get_get_ingredient_use_case),
) -> IngredientResponse:

    ingredient = await use_case.execute(ingredient_id)

    return IngredientResponse.model_validate(ingredient, from_attributes=True, context=language_context(current_user))
