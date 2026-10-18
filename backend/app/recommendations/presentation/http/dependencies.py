"""
Composition root for the recommendations module.

Wires the session repository, the scorer and the anti-corruption-layer
adapters. Other bounded contexts are reached only through their public
seams: IAM's `get_current_user` and the Open Host Services of recipes,
ingredients, equipment and portfolio.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.equipment.application.public.equipment_query_service import EquipmentQueryService
from app.equipment.presentation.http.dependencies import get_equipment_query_service
from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.ingredients.presentation.http.dependencies import get_ingredient_query_service
from app.portfolio.application.public.favorites_service import FavoritesService
from app.portfolio.presentation.http.dependencies import get_favorites_service
from app.recipes.application.public.recipe_query_service import RecipeQueryService
from app.recipes.presentation.http.dependencies import get_recipe_query_service
from app.recommendations.application.use_cases.deck_use_cases import (
    GetRecommendationDeckUseCase,
    SwipeRecipeUseCase,
)
from app.recommendations.application.use_cases.session_use_cases import (
    GetDiscoverySessionUseCase,
    ListSwipesUseCase,
    StartDiscoverySessionUseCase,
)
from app.recommendations.domain.repositories.discovery_session_repository import DiscoverySessionRepository
from app.recommendations.domain.services.compatibility_scorer import CompatibilityScorer
from app.recommendations.domain.services.ports import FavoritesGateway, KitchenCatalog, RecipeCandidateSource
from app.recommendations.infraestructure.catalog.acl_adapters import (
    KitchenModulesCatalog,
    PortfolioFavoritesGateway,
    RecipesModuleCandidateSource,
)
from app.recommendations.infraestructure.persistence.repositories.sqlalchemy_discovery_session_repository import (
    SqlAlchemyDiscoverySessionRepository,
)
from app.shared.database.session import get_db_session

# --- Repositories / ports -----------------------------------------------------------


def get_discovery_session_repository(
    session: AsyncSession = Depends(get_db_session),
) -> DiscoverySessionRepository:
    return SqlAlchemyDiscoverySessionRepository(session)


def get_recipe_candidate_source(
    recipes: RecipeQueryService = Depends(get_recipe_query_service),
) -> RecipeCandidateSource:
    return RecipesModuleCandidateSource(recipes)


def get_kitchen_catalog(
    ingredients: IngredientQueryService = Depends(get_ingredient_query_service),
    equipment: EquipmentQueryService = Depends(get_equipment_query_service),
) -> KitchenCatalog:
    return KitchenModulesCatalog(ingredients, equipment)


def get_favorites_gateway(favorites: FavoritesService = Depends(get_favorites_service)) -> FavoritesGateway:
    return PortfolioFavoritesGateway(favorites)


def get_compatibility_scorer() -> CompatibilityScorer:
    return CompatibilityScorer()


# --- Use cases ------------------------------------------------------------------------


def get_start_discovery_session_use_case(
    session_repository: DiscoverySessionRepository = Depends(get_discovery_session_repository),
    kitchen: KitchenCatalog = Depends(get_kitchen_catalog),
    recipe_source: RecipeCandidateSource = Depends(get_recipe_candidate_source),
) -> StartDiscoverySessionUseCase:
    return StartDiscoverySessionUseCase(session_repository, kitchen, recipe_source)


def get_get_discovery_session_use_case(
    session_repository: DiscoverySessionRepository = Depends(get_discovery_session_repository),
    kitchen: KitchenCatalog = Depends(get_kitchen_catalog),
    recipe_source: RecipeCandidateSource = Depends(get_recipe_candidate_source),
) -> GetDiscoverySessionUseCase:
    return GetDiscoverySessionUseCase(session_repository, kitchen, recipe_source)


def get_list_swipes_use_case(
    session_repository: DiscoverySessionRepository = Depends(get_discovery_session_repository),
) -> ListSwipesUseCase:
    return ListSwipesUseCase(session_repository)


def get_recommendation_deck_use_case(
    session_repository: DiscoverySessionRepository = Depends(get_discovery_session_repository),
    recipe_source: RecipeCandidateSource = Depends(get_recipe_candidate_source),
    kitchen: KitchenCatalog = Depends(get_kitchen_catalog),
    favorites: FavoritesGateway = Depends(get_favorites_gateway),
    scorer: CompatibilityScorer = Depends(get_compatibility_scorer),
) -> GetRecommendationDeckUseCase:
    return GetRecommendationDeckUseCase(session_repository, recipe_source, kitchen, favorites, scorer)


def get_swipe_recipe_use_case(
    session_repository: DiscoverySessionRepository = Depends(get_discovery_session_repository),
    recipe_source: RecipeCandidateSource = Depends(get_recipe_candidate_source),
    kitchen: KitchenCatalog = Depends(get_kitchen_catalog),
    favorites: FavoritesGateway = Depends(get_favorites_gateway),
    scorer: CompatibilityScorer = Depends(get_compatibility_scorer),
) -> SwipeRecipeUseCase:
    return SwipeRecipeUseCase(session_repository, recipe_source, kitchen, favorites, scorer)
