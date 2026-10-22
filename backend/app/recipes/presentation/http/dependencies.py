"""
Composition root for the recipes module.

Wires domain interfaces to their SQLAlchemy implementations and builds each
use case. Other bounded contexts are reached only through their public
seams: IAM's `get_current_user`, the ingredients module's
`IngredientQueryService` and the equipment module's `EquipmentQueryService`
(each wrapped by our anti-corruption layer).
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.equipment.application.public.equipment_query_service import EquipmentQueryService
from app.equipment.presentation.http.dependencies import get_equipment_query_service
from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.ingredients.presentation.http.dependencies import get_ingredient_query_service
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.application.public.recipe_query_service import RecipeQueryService
from app.recipes.application.services.recipe_reference_validator import RecipeReferenceValidator
from app.recipes.application.use_cases.create_recipe_use_case import CreateRecipeUseCase
from app.recipes.application.use_cases.delete_recipe_use_case import DeleteRecipeUseCase
from app.recipes.application.use_cases.get_recipe_use_case import GetRecipeUseCase
from app.recipes.application.use_cases.list_my_recipes_use_case import ListMyRecipesUseCase
from app.recipes.application.use_cases.list_personalizations_use_case import ListPersonalizationsUseCase
from app.recipes.application.use_cases.list_recipe_catalogs_use_cases import (
    ListDifficultiesUseCase,
    ListRecipeCategoriesUseCase,
    ListRecipeTagsUseCase,
)
from app.recipes.application.use_cases.personalize_recipe_use_case import PersonalizeRecipeUseCase
from app.recipes.application.use_cases.recipe_photo_use_cases import (
    AddRecipePhotoUseCase,
    ListRecipePhotosUseCase,
    RemoveRecipePhotoUseCase,
    ReorderCoverPhotosUseCase,
)
from app.recipes.application.use_cases.replace_recipe_equipment_use_case import ReplaceRecipeEquipmentUseCase
from app.recipes.application.use_cases.replace_recipe_ingredients_use_case import (
    ReplaceRecipeIngredientsUseCase,
)
from app.recipes.application.use_cases.replace_recipe_steps_use_case import ReplaceRecipeStepsUseCase
from app.recipes.application.use_cases.replace_recipe_tags_use_case import ReplaceRecipeTagsUseCase
from app.recipes.application.use_cases.search_public_recipes_use_case import SearchPublicRecipesUseCase
from app.recipes.application.use_cases.update_recipe_use_case import UpdateRecipeUseCase
from app.recipes.domain.repositories.recipe_catalog_repositories import (
    DifficultyRepository,
    RecipeCategoryRepository,
    RecipeTagRepository,
)
from app.recipes.domain.repositories.recipe_repository import RecipeRepository
from app.recipes.domain.services.equipment_catalog import EquipmentCatalog
from app.recipes.domain.services.ingredient_catalog import IngredientCatalog
from app.recipes.infraestructure.catalog.equipment_module_catalog import EquipmentModuleCatalog
from app.recipes.infraestructure.catalog.ingredients_module_catalog import IngredientsModuleCatalog
from app.recipes.infraestructure.persistence.repositories.sqlalchemy_recipe_catalog_repositories import (
    SqlAlchemyDifficultyRepository,
    SqlAlchemyRecipeCategoryRepository,
    SqlAlchemyRecipeTagRepository,
)
from app.recipes.infraestructure.persistence.repositories.sqlalchemy_recipe_repository import (
    SqlAlchemyRecipeRepository,
)
from app.shared.database.session import get_db_session

# --- Repositories / ports -----------------------------------------------------------


def get_recipe_repository(session: AsyncSession = Depends(get_db_session)) -> RecipeRepository:
    return SqlAlchemyRecipeRepository(session)


def get_recipe_category_repository(session: AsyncSession = Depends(get_db_session)) -> RecipeCategoryRepository:
    return SqlAlchemyRecipeCategoryRepository(session)


def get_difficulty_repository(session: AsyncSession = Depends(get_db_session)) -> DifficultyRepository:
    return SqlAlchemyDifficultyRepository(session)


def get_recipe_tag_repository(session: AsyncSession = Depends(get_db_session)) -> RecipeTagRepository:
    return SqlAlchemyRecipeTagRepository(session)


def get_ingredient_catalog(
    ingredients: IngredientQueryService = Depends(get_ingredient_query_service),
) -> IngredientCatalog:
    return IngredientsModuleCatalog(ingredients)


def get_equipment_catalog(
    equipment: EquipmentQueryService = Depends(get_equipment_query_service),
) -> EquipmentCatalog:
    return EquipmentModuleCatalog(equipment)


# --- Application services -----------------------------------------------------------


def get_recipe_assembler(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    category_repository: RecipeCategoryRepository = Depends(get_recipe_category_repository),
    difficulty_repository: DifficultyRepository = Depends(get_difficulty_repository),
    ingredient_catalog: IngredientCatalog = Depends(get_ingredient_catalog),
    equipment_catalog: EquipmentCatalog = Depends(get_equipment_catalog),
    tag_repository: RecipeTagRepository = Depends(get_recipe_tag_repository),
) -> RecipeAssembler:
    return RecipeAssembler(
        recipe_repository,
        category_repository,
        difficulty_repository,
        ingredient_catalog,
        equipment_catalog,
        tag_repository,
    )


def get_recipe_reference_validator(
    category_repository: RecipeCategoryRepository = Depends(get_recipe_category_repository),
    difficulty_repository: DifficultyRepository = Depends(get_difficulty_repository),
    ingredient_catalog: IngredientCatalog = Depends(get_ingredient_catalog),
    equipment_catalog: EquipmentCatalog = Depends(get_equipment_catalog),
    tag_repository: RecipeTagRepository = Depends(get_recipe_tag_repository),
) -> RecipeReferenceValidator:
    return RecipeReferenceValidator(
        category_repository, difficulty_repository, ingredient_catalog, equipment_catalog, tag_repository
    )


# --- Use cases ------------------------------------------------------------------------


def get_create_recipe_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    reference_validator: RecipeReferenceValidator = Depends(get_recipe_reference_validator),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> CreateRecipeUseCase:
    return CreateRecipeUseCase(recipe_repository, reference_validator, assembler)


def get_get_recipe_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> GetRecipeUseCase:
    return GetRecipeUseCase(recipe_repository, assembler)


def get_search_public_recipes_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> SearchPublicRecipesUseCase:
    return SearchPublicRecipesUseCase(recipe_repository, assembler)


def get_list_my_recipes_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> ListMyRecipesUseCase:
    return ListMyRecipesUseCase(recipe_repository, assembler)


def get_update_recipe_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    reference_validator: RecipeReferenceValidator = Depends(get_recipe_reference_validator),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> UpdateRecipeUseCase:
    return UpdateRecipeUseCase(recipe_repository, reference_validator, assembler)


def get_replace_recipe_ingredients_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    reference_validator: RecipeReferenceValidator = Depends(get_recipe_reference_validator),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> ReplaceRecipeIngredientsUseCase:
    return ReplaceRecipeIngredientsUseCase(recipe_repository, reference_validator, assembler)


def get_replace_recipe_equipment_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    reference_validator: RecipeReferenceValidator = Depends(get_recipe_reference_validator),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> ReplaceRecipeEquipmentUseCase:
    return ReplaceRecipeEquipmentUseCase(recipe_repository, reference_validator, assembler)


def get_replace_recipe_tags_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    reference_validator: RecipeReferenceValidator = Depends(get_recipe_reference_validator),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> ReplaceRecipeTagsUseCase:
    return ReplaceRecipeTagsUseCase(recipe_repository, reference_validator, assembler)


def get_replace_recipe_steps_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> ReplaceRecipeStepsUseCase:
    return ReplaceRecipeStepsUseCase(recipe_repository, assembler)


def get_delete_recipe_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
) -> DeleteRecipeUseCase:
    return DeleteRecipeUseCase(recipe_repository)


def get_personalize_recipe_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> PersonalizeRecipeUseCase:
    return PersonalizeRecipeUseCase(recipe_repository, assembler)


def get_list_personalizations_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
) -> ListPersonalizationsUseCase:
    return ListPersonalizationsUseCase(recipe_repository, assembler)


def get_list_recipe_photos_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
) -> ListRecipePhotosUseCase:
    return ListRecipePhotosUseCase(recipe_repository)


def get_add_recipe_photo_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
) -> AddRecipePhotoUseCase:
    return AddRecipePhotoUseCase(recipe_repository)


def get_remove_recipe_photo_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
) -> RemoveRecipePhotoUseCase:
    return RemoveRecipePhotoUseCase(recipe_repository)


def get_reorder_cover_photos_use_case(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
) -> ReorderCoverPhotosUseCase:
    return ReorderCoverPhotosUseCase(recipe_repository)


def get_list_recipe_categories_use_case(
    category_repository: RecipeCategoryRepository = Depends(get_recipe_category_repository),
) -> ListRecipeCategoriesUseCase:
    return ListRecipeCategoriesUseCase(category_repository)


def get_list_recipe_tags_use_case(
    tag_repository: RecipeTagRepository = Depends(get_recipe_tag_repository),
) -> ListRecipeTagsUseCase:
    return ListRecipeTagsUseCase(tag_repository)


def get_list_difficulties_use_case(
    difficulty_repository: DifficultyRepository = Depends(get_difficulty_repository),
) -> ListDifficultiesUseCase:
    return ListDifficultiesUseCase(difficulty_repository)


# --- Public API for other bounded contexts ---------------------------------------


def get_recipe_query_service(
    recipe_repository: RecipeRepository = Depends(get_recipe_repository),
    assembler: RecipeAssembler = Depends(get_recipe_assembler),
    category_repository: RecipeCategoryRepository = Depends(get_recipe_category_repository),
    tag_repository: RecipeTagRepository = Depends(get_recipe_tag_repository),
    difficulty_repository: DifficultyRepository = Depends(get_difficulty_repository),
) -> RecipeQueryService:
    """Provider other modules' composition roots use to reach the recipes Open Host Service."""
    return RecipeQueryService(recipe_repository, assembler, category_repository, tag_repository, difficulty_repository)
