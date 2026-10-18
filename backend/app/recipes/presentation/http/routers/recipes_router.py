"""
Recipes: CRUD, public search ("Explorar"), "my recipes" and personalization.

Every endpoint requires authentication. A private recipe of another user
answers 404 (never 403), so its existence is not revealed.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.recipes.application.dto.recipe_dto import (
    CreateRecipeDTO,
    RecipeEquipmentInputDTO,
    RecipeIngredientInputDTO,
    RecipeStepInputDTO,
    SearchRecipesDTO,
    UpdateRecipeDTO,
)
from app.recipes.application.use_cases.create_recipe_use_case import CreateRecipeUseCase
from app.recipes.application.use_cases.delete_recipe_use_case import DeleteRecipeUseCase
from app.recipes.application.use_cases.get_recipe_use_case import GetRecipeUseCase
from app.recipes.application.use_cases.list_my_recipes_use_case import ListMyRecipesUseCase
from app.recipes.application.use_cases.list_personalizations_use_case import ListPersonalizationsUseCase
from app.recipes.application.use_cases.personalize_recipe_use_case import PersonalizeRecipeUseCase
from app.recipes.application.use_cases.replace_recipe_equipment_use_case import ReplaceRecipeEquipmentUseCase
from app.recipes.application.use_cases.replace_recipe_ingredients_use_case import (
    ReplaceRecipeIngredientsUseCase,
)
from app.recipes.application.use_cases.replace_recipe_steps_use_case import ReplaceRecipeStepsUseCase
from app.recipes.application.use_cases.replace_recipe_tags_use_case import ReplaceRecipeTagsUseCase
from app.recipes.application.use_cases.search_public_recipes_use_case import SearchPublicRecipesUseCase
from app.recipes.application.use_cases.update_recipe_use_case import UpdateRecipeUseCase
from app.recipes.presentation.http.dependencies import (
    get_create_recipe_use_case,
    get_delete_recipe_use_case,
    get_get_recipe_use_case,
    get_list_my_recipes_use_case,
    get_list_personalizations_use_case,
    get_personalize_recipe_use_case,
    get_replace_recipe_equipment_use_case,
    get_replace_recipe_ingredients_use_case,
    get_replace_recipe_steps_use_case,
    get_replace_recipe_tags_use_case,
    get_search_public_recipes_use_case,
    get_update_recipe_use_case,
)
from app.recipes.presentation.http.schemas.recipe_schemas import (
    CreateRecipeRequest,
    PersonalizeRecipeRequest,
    RecipeDetailResponse,
    RecipeEquipmentRequest,
    RecipeIngredientRequest,
    RecipeStepRequest,
    RecipeSummaryResponse,
    ReplaceEquipmentRequest,
    ReplaceIngredientsRequest,
    ReplaceStepsRequest,
    ReplaceTagsRequest,
    UpdateRecipeRequest,
)
from app.shared.exceptions.domain_exceptions import ValidationError
from app.shared.presentation.pagination import PageResponse

router = APIRouter(prefix="/recipes", tags=["Recipes"])


def _ingredient_inputs(items: list[RecipeIngredientRequest]) -> list[RecipeIngredientInputDTO]:
    return [RecipeIngredientInputDTO(**item.model_dump()) for item in items]


def _equipment_inputs(items: list[RecipeEquipmentRequest]) -> list[RecipeEquipmentInputDTO]:
    return [RecipeEquipmentInputDTO(**item.model_dump()) for item in items]


def _step_inputs(items: list[RecipeStepRequest]) -> list[RecipeStepInputDTO]:
    return [RecipeStepInputDTO(**item.model_dump()) for item in items]


def _set_location(http_request: Request, response: Response, recipe_id: str) -> None:
    response.headers["Location"] = str(http_request.url_for("get_recipe", recipe_id=recipe_id))


@router.get("", response_model=PageResponse[RecipeSummaryResponse])
async def search_public_recipes(
    q: str | None = Query(default=None, description="Text to look for in title or description"),
    category_id: str | None = None,
    difficulty_id: str | None = None,
    max_prep_time: int | None = Query(default=None, gt=0, description="Maximum preparation time, in minutes"),
    ingredient_ids: list[str] = Query(default=[], description="Recipe must use all of these ingredients"),
    tag_ids: list[str] = Query(default=[], description="Recipe must have all of these tags"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: SearchPublicRecipesUseCase = Depends(get_search_public_recipes_use_case),
) -> PageResponse[RecipeSummaryResponse]:
    dto = SearchRecipesDTO(
        query=q,
        category_id=category_id,
        difficulty_id=difficulty_id,
        max_prep_time_minutes=max_prep_time,
        ingredient_ids=ingredient_ids,
        tag_ids=tag_ids,
        limit=limit,
        offset=offset,
    )
    page = await use_case.execute(dto, current_user.id)
    return PageResponse[RecipeSummaryResponse].model_validate(page, from_attributes=True)


@router.post("", response_model=RecipeDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    request: CreateRecipeRequest,
    http_request: Request,
    response: Response,
    current_user: UserDTO = Depends(get_current_user),
    use_case: CreateRecipeUseCase = Depends(get_create_recipe_use_case),
) -> RecipeDetailResponse:
    dto = CreateRecipeDTO(
        user_id=current_user.id,
        title=request.title,
        description=request.description,
        video_url=request.video_url,
        category_id=request.category_id,
        difficulty_id=request.difficulty_id,
        prep_time_minutes=request.prep_time_minutes,
        servings=request.servings,
        is_public=request.is_public,
        ingredients=_ingredient_inputs(request.ingredients),
        equipment=_equipment_inputs(request.equipment),
        tag_ids=request.tag_ids,
        steps=_step_inputs(request.steps),
    )
    recipe = await use_case.execute(dto)
    _set_location(http_request, response, recipe.id)
    return RecipeDetailResponse.model_validate(recipe, from_attributes=True)


@router.get("/mine", response_model=PageResponse[RecipeSummaryResponse])
async def list_my_recipes(
    kind: Literal["original", "personalized"] | None = Query(
        default=None, description="Only originals, only personalizations, or both when omitted"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListMyRecipesUseCase = Depends(get_list_my_recipes_use_case),
) -> PageResponse[RecipeSummaryResponse]:
    page = await use_case.execute(current_user.id, kind, limit=limit, offset=offset)
    return PageResponse[RecipeSummaryResponse].model_validate(page, from_attributes=True)


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
async def get_recipe(
    recipe_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: GetRecipeUseCase = Depends(get_get_recipe_use_case),
) -> RecipeDetailResponse:
    recipe = await use_case.execute(recipe_id, current_user.id)
    return RecipeDetailResponse.model_validate(recipe, from_attributes=True)


@router.patch("/{recipe_id}", response_model=RecipeDetailResponse)
async def update_recipe(
    recipe_id: str,
    request: UpdateRecipeRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: UpdateRecipeUseCase = Depends(get_update_recipe_use_case),
) -> RecipeDetailResponse:
    changes = request.model_dump(exclude_unset=True)
    for non_nullable in ("title", "is_public"):
        if non_nullable in changes and changes[non_nullable] is None:
            raise ValidationError(f"'{non_nullable}' cannot be null")
    recipe = await use_case.execute(UpdateRecipeDTO(user_id=current_user.id, recipe_id=recipe_id, changes=changes))
    return RecipeDetailResponse.model_validate(recipe, from_attributes=True)


@router.put("/{recipe_id}/ingredients", response_model=RecipeDetailResponse)
async def replace_recipe_ingredients(
    recipe_id: str,
    request: ReplaceIngredientsRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: ReplaceRecipeIngredientsUseCase = Depends(get_replace_recipe_ingredients_use_case),
) -> RecipeDetailResponse:
    recipe = await use_case.execute(current_user.id, recipe_id, _ingredient_inputs(request.ingredients))
    return RecipeDetailResponse.model_validate(recipe, from_attributes=True)


@router.put("/{recipe_id}/equipment", response_model=RecipeDetailResponse)
async def replace_recipe_equipment(
    recipe_id: str,
    request: ReplaceEquipmentRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: ReplaceRecipeEquipmentUseCase = Depends(get_replace_recipe_equipment_use_case),
) -> RecipeDetailResponse:
    recipe = await use_case.execute(current_user.id, recipe_id, _equipment_inputs(request.equipment))
    return RecipeDetailResponse.model_validate(recipe, from_attributes=True)


@router.put("/{recipe_id}/tags", response_model=RecipeDetailResponse)
async def replace_recipe_tags(
    recipe_id: str,
    request: ReplaceTagsRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: ReplaceRecipeTagsUseCase = Depends(get_replace_recipe_tags_use_case),
) -> RecipeDetailResponse:
    recipe = await use_case.execute(current_user.id, recipe_id, request.tag_ids)
    return RecipeDetailResponse.model_validate(recipe, from_attributes=True)


@router.put("/{recipe_id}/steps", response_model=RecipeDetailResponse)
async def replace_recipe_steps(
    recipe_id: str,
    request: ReplaceStepsRequest,
    current_user: UserDTO = Depends(get_current_user),
    use_case: ReplaceRecipeStepsUseCase = Depends(get_replace_recipe_steps_use_case),
) -> RecipeDetailResponse:
    recipe = await use_case.execute(current_user.id, recipe_id, _step_inputs(request.steps))
    return RecipeDetailResponse.model_validate(recipe, from_attributes=True)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: str,
    current_user: UserDTO = Depends(get_current_user),
    use_case: DeleteRecipeUseCase = Depends(get_delete_recipe_use_case),
) -> None:
    await use_case.execute(current_user.id, recipe_id)


@router.post(
    "/{recipe_id}/personalizations", response_model=RecipeDetailResponse, status_code=status.HTTP_201_CREATED
)
async def personalize_recipe(
    recipe_id: str,
    http_request: Request,
    response: Response,
    request: PersonalizeRecipeRequest | None = None,
    current_user: UserDTO = Depends(get_current_user),
    use_case: PersonalizeRecipeUseCase = Depends(get_personalize_recipe_use_case),
) -> RecipeDetailResponse:
    recipe = await use_case.execute(current_user.id, recipe_id, title=request.title if request else None)
    _set_location(http_request, response, recipe.id)
    return RecipeDetailResponse.model_validate(recipe, from_attributes=True)


@router.get("/{recipe_id}/personalizations", response_model=PageResponse[RecipeSummaryResponse])
async def list_my_personalizations(
    recipe_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListPersonalizationsUseCase = Depends(get_list_personalizations_use_case),
) -> PageResponse[RecipeSummaryResponse]:
    page = await use_case.execute(current_user.id, recipe_id, limit=limit, offset=offset)
    return PageResponse[RecipeSummaryResponse].model_validate(page, from_attributes=True)
