"""
Recipe catalogs: categories (`/recipe-categories`), difficulty levels
(`/difficulties`) and tags (`/recipe-tags`). All are seeded by migration. `/recipe-categories` is a
controlled list, distinct from the free-text ingredient `/categories`.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.iam.application.dto.user_dto import UserDTO
from app.iam.presentation.http.dependencies import get_current_user
from app.recipes.application.use_cases.list_recipe_catalogs_use_cases import (
    ListDifficultiesUseCase,
    ListRecipeCategoriesUseCase,
    ListRecipeTagsUseCase,
)
from app.recipes.presentation.http.dependencies import (
    get_list_difficulties_use_case,
    get_list_recipe_categories_use_case,
    get_list_recipe_tags_use_case,
)
from app.recipes.presentation.http.schemas.recipe_schemas import (
    DifficultyResponse,
    RecipeCategoryResponse,
    RecipeTagResponse,
)
from app.shared.presentation.i18n import language_context

router = APIRouter()


@router.get("/recipe-categories", response_model=list[RecipeCategoryResponse], tags=["Recipe categories"])
async def list_recipe_categories(
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListRecipeCategoriesUseCase = Depends(get_list_recipe_categories_use_case),
) -> list[RecipeCategoryResponse]:
    return [RecipeCategoryResponse.model_validate(category, from_attributes=True, context=language_context(current_user)) for category in await use_case.execute()]


@router.get("/difficulties", response_model=list[DifficultyResponse], tags=["Difficulties"])
async def list_difficulties(
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListDifficultiesUseCase = Depends(get_list_difficulties_use_case),
) -> list[DifficultyResponse]:
    return [DifficultyResponse.model_validate(difficulty, from_attributes=True, context=language_context(current_user)) for difficulty in await use_case.execute()]


@router.get("/recipe-tags", response_model=list[RecipeTagResponse], tags=["Recipe tags"])
async def list_recipe_tags(
    group: Literal["sabor", "dieta", "tecnica", "tiempo", "celebraciones"] | None = Query(
        default=None, description="Only the tags of this group"
    ),
    current_user: UserDTO = Depends(get_current_user),
    use_case: ListRecipeTagsUseCase = Depends(get_list_recipe_tags_use_case),
) -> list[RecipeTagResponse]:
    return [RecipeTagResponse.model_validate(tag, from_attributes=True, context=language_context(current_user)) for tag in await use_case.execute(group)]
