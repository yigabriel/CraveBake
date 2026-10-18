"""
Anti-corruption layer: implements recommendations' ports on top of the
public APIs (Open Host Services) of recipes, ingredients, equipment and
portfolio, translating their DTOs into this module's own types.

Recommendations never touches another module's tables or domain; if any of
them changes internally, only its public contract has to hold.
"""
from __future__ import annotations

from app.equipment.application.public.equipment_query_service import EquipmentQueryService
from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.portfolio.application.public.favorites_service import FavoritesService
from app.recipes.application.dto.recipe_dto import IngredientOverlapQueryDTO, RecipeCompositionDTO
from app.recipes.application.public.recipe_query_service import RecipeQueryService
from app.recommendations.domain.services.ports import (
    CandidateRankingPage,
    CandidateRankingRequest,
    CandidateRecipe,
    FavoritesGateway,
    KitchenCatalog,
    RecipeCandidateSource,
)


class RecipesModuleCandidateSource(RecipeCandidateSource):
    def __init__(self, recipes: RecipeQueryService) -> None:
        self._recipes = recipes

    async def rank(self, request: CandidateRankingRequest) -> CandidateRankingPage:
        ranked = await self._recipes.rank_by_ingredient_overlap(
            IngredientOverlapQueryDTO(
                viewer_user_id=request.viewer_user_id,
                ingredient_ids=request.ingredient_ids,
                equipment_ids=request.equipment_ids,
                ingredient_weight=request.ingredient_weight,
                equipment_weight=request.equipment_weight,
                min_ingredient_score=request.min_ingredient_score,
                excluded_recipe_ids=request.excluded_recipe_ids,
                category_id=request.category_id,
                tag_ids=request.tag_ids,
                limit=request.limit,
                offset=request.offset,
            )
        )
        return CandidateRankingPage(recipe_ids=ranked.recipe_ids, total=ranked.total)

    async def get_many_visible(self, recipe_ids: list[str], viewer_user_id: str) -> list[CandidateRecipe]:
        return [_to_candidate(item) for item in await self._recipes.get_compositions(recipe_ids, viewer_user_id)]

    async def get_visible(self, recipe_id: str, viewer_user_id: str) -> CandidateRecipe | None:
        composition = await self._recipes.get_composition(recipe_id, viewer_user_id)
        return _to_candidate(composition) if composition else None

    async def category_names(self) -> dict[str, str]:
        return {category.id: category.name for category in await self._recipes.list_categories()}

    async def tag_names(self) -> dict[str, str]:
        return {tag.id: tag.name for tag in await self._recipes.list_tags()}


class KitchenModulesCatalog(KitchenCatalog):
    def __init__(self, ingredients: IngredientQueryService, equipment: EquipmentQueryService) -> None:
        self._ingredients = ingredients
        self._equipment = equipment

    async def pantry_ingredient_ids(self, user_id: str) -> list[str]:
        return await self._ingredients.list_pantry_ingredient_ids(user_id)

    async def user_equipment_ids(self, user_id: str) -> list[str]:
        return await self._equipment.list_user_equipment_ids(user_id)

    async def ingredient_names(self, ids: list[str]) -> dict[str, str]:
        return {item.id: item.name for item in await self._ingredients.get_ingredients(ids)}

    async def equipment_names(self, ids: list[str]) -> dict[str, str]:
        return {item.id: item.name for item in await self._equipment.get_equipment(ids)}


class PortfolioFavoritesGateway(FavoritesGateway):
    def __init__(self, favorites: FavoritesService) -> None:
        self._favorites = favorites

    async def save(self, user_id: str, recipe_id: str) -> None:
        await self._favorites.save(user_id, recipe_id)

    async def saved_among(self, user_id: str, recipe_ids: list[str]) -> set[str]:
        return await self._favorites.saved_among(user_id, recipe_ids)


def _to_candidate(composition: RecipeCompositionDTO) -> CandidateRecipe:
    recipe = composition.recipe
    return CandidateRecipe(
        id=recipe.id,
        title=recipe.title,
        description=recipe.description,
        cover_photo_url=recipe.cover_photo_url,
        category_name=recipe.category.name if recipe.category else None,
        difficulty_name=recipe.difficulty.name if recipe.difficulty else None,
        prep_time_minutes=recipe.prep_time_minutes,
        servings=recipe.servings,
        created_by_user_id=recipe.created_by_user_id,
        is_personalization=recipe.is_personalization,
        source_recipe_title=recipe.source_recipe_title,
        tag_names=tuple(tag.name for tag in recipe.tags),
        ingredient_ids=frozenset(composition.ingredient_ids),
        equipment_ids=frozenset(composition.equipment_ids),
    )
