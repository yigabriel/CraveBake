"""
Composition root for the preparation module.

Other bounded contexts are reached only through their public seams: IAM's
`get_current_user` and the Open Host Services of recipes and ingredients,
each wrapped by our anti-corruption layer.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.ingredients.presentation.http.dependencies import get_ingredient_query_service
from app.preparation.application.mappers.preparation_assembler import PreparationAssembler
from app.preparation.application.use_cases.preparation_use_cases import (
    GetPreparationUseCase,
    ListPreparationsUseCase,
    PreparationProgressUseCases,
    StartPreparationUseCase,
)
from app.preparation.domain.repositories.preparation_session_repository import PreparationSessionRepository
from app.preparation.domain.services.ports import QuantityDisplay, RecipeSource
from app.preparation.infraestructure.catalog.acl_adapters import IngredientsQuantityDisplay, RecipesModuleSource
from app.preparation.infraestructure.persistence.repositories.sqlalchemy_preparation_session_repository import (
    SqlAlchemyPreparationSessionRepository,
)
from app.recipes.application.public.recipe_query_service import RecipeQueryService
from app.recipes.presentation.http.dependencies import get_recipe_query_service
from app.shared.database.session import get_db_session


def get_preparation_repository(session: AsyncSession = Depends(get_db_session)) -> PreparationSessionRepository:
    return SqlAlchemyPreparationSessionRepository(session)


def get_recipe_source(recipes: RecipeQueryService = Depends(get_recipe_query_service)) -> RecipeSource:
    return RecipesModuleSource(recipes)


def get_quantity_display(
    ingredients: IngredientQueryService = Depends(get_ingredient_query_service),
) -> QuantityDisplay:
    return IngredientsQuantityDisplay(ingredients)


def get_preparation_assembler(quantity_display: QuantityDisplay = Depends(get_quantity_display)) -> PreparationAssembler:
    return PreparationAssembler(quantity_display)


def get_start_preparation_use_case(
    repository: PreparationSessionRepository = Depends(get_preparation_repository),
    recipe_source: RecipeSource = Depends(get_recipe_source),
    assembler: PreparationAssembler = Depends(get_preparation_assembler),
) -> StartPreparationUseCase:
    return StartPreparationUseCase(repository, recipe_source, assembler)


def get_get_preparation_use_case(
    repository: PreparationSessionRepository = Depends(get_preparation_repository),
    assembler: PreparationAssembler = Depends(get_preparation_assembler),
) -> GetPreparationUseCase:
    return GetPreparationUseCase(repository, assembler)


def get_list_preparations_use_case(
    repository: PreparationSessionRepository = Depends(get_preparation_repository),
) -> ListPreparationsUseCase:
    return ListPreparationsUseCase(repository)


def get_preparation_progress_use_cases(
    repository: PreparationSessionRepository = Depends(get_preparation_repository),
    assembler: PreparationAssembler = Depends(get_preparation_assembler),
) -> PreparationProgressUseCases:
    return PreparationProgressUseCases(repository, assembler)
