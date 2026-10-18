"""
Composition root for the portfolio module.

Wires domain interfaces to their implementations and builds each use case.
Other bounded contexts are reached only through their public seams: IAM's
`get_current_user` and the recipes module's `RecipeQueryService` (wrapped
by our anti-corruption layer).
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.application.public.favorites_service import FavoritesService
from app.portfolio.application.use_cases.favorite_use_cases import (
    GetFavoriteStatusUseCase,
    SaveRecipeUseCase,
    UnsaveRecipeUseCase,
)
from app.portfolio.application.use_cases.get_portfolio_summary_use_case import GetPortfolioSummaryUseCase
from app.portfolio.application.use_cases.get_portfolio_use_case import GetPortfolioUseCase
from app.portfolio.application.use_cases.portfolio_reader import PortfolioReader
from app.portfolio.domain.repositories.saved_recipe_repository import SavedRecipeRepository
from app.portfolio.domain.services.recipe_catalog import RecipeCatalog
from app.portfolio.infraestructure.catalog.recipes_module_catalog import RecipesModuleCatalog
from app.portfolio.infraestructure.persistence.repositories.sqlalchemy_saved_recipe_repository import (
    SqlAlchemySavedRecipeRepository,
)
from app.recipes.application.public.recipe_query_service import RecipeQueryService
from app.recipes.presentation.http.dependencies import get_recipe_query_service
from app.shared.database.session import get_db_session

# --- Repositories / ports -----------------------------------------------------------


def get_saved_recipe_repository(session: AsyncSession = Depends(get_db_session)) -> SavedRecipeRepository:
    return SqlAlchemySavedRecipeRepository(session)


def get_recipe_catalog(recipes: RecipeQueryService = Depends(get_recipe_query_service)) -> RecipeCatalog:
    return RecipesModuleCatalog(recipes)


def get_portfolio_reader(
    saved_recipe_repository: SavedRecipeRepository = Depends(get_saved_recipe_repository),
    recipe_catalog: RecipeCatalog = Depends(get_recipe_catalog),
) -> PortfolioReader:
    return PortfolioReader(saved_recipe_repository, recipe_catalog)


# --- Use cases ------------------------------------------------------------------------


def get_get_portfolio_use_case(
    portfolio_reader: PortfolioReader = Depends(get_portfolio_reader),
) -> GetPortfolioUseCase:
    return GetPortfolioUseCase(portfolio_reader)


def get_get_portfolio_summary_use_case(
    portfolio_reader: PortfolioReader = Depends(get_portfolio_reader),
) -> GetPortfolioSummaryUseCase:
    return GetPortfolioSummaryUseCase(portfolio_reader)


def get_save_recipe_use_case(
    saved_recipe_repository: SavedRecipeRepository = Depends(get_saved_recipe_repository),
    recipe_catalog: RecipeCatalog = Depends(get_recipe_catalog),
) -> SaveRecipeUseCase:
    return SaveRecipeUseCase(saved_recipe_repository, recipe_catalog)


def get_unsave_recipe_use_case(
    saved_recipe_repository: SavedRecipeRepository = Depends(get_saved_recipe_repository),
) -> UnsaveRecipeUseCase:
    return UnsaveRecipeUseCase(saved_recipe_repository)


def get_favorite_status_use_case(
    saved_recipe_repository: SavedRecipeRepository = Depends(get_saved_recipe_repository),
) -> GetFavoriteStatusUseCase:
    return GetFavoriteStatusUseCase(saved_recipe_repository)


# --- Public API for other bounded contexts ---------------------------------------


def get_favorites_service(
    save_recipe_use_case: SaveRecipeUseCase = Depends(get_save_recipe_use_case),
    saved_recipe_repository: SavedRecipeRepository = Depends(get_saved_recipe_repository),
) -> FavoritesService:
    """Provider other modules' composition roots use to reach the portfolio Open Host Service."""
    return FavoritesService(save_recipe_use_case, saved_recipe_repository)
