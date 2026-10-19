"""
Deck use cases: get the next recommendations and swipe them.

The deck holds every recipe the user can see — public ones and their own;
a personalization replaces the original it came from — that uses at least
one of the session's ingredients and matches its filters (category, tags,
`min_score`), minus whatever was already swiped in this session.

Ranking happens in the database (`RecipeCandidateSource.rank`), driven by
this module's `CompatibilityScorer` weights, so only the requested page of
recipes is ever loaded. Each card on that page is then scored here to
explain itself: what matches, what is missing.
"""
from __future__ import annotations

from app.recommendations.application.dto.recommendation_dto import NamedRefDTO, RecommendationDTO, SwipeDTO
from app.recommendations.application.use_cases.session_use_cases import load_owned_session, swipe_to_dto
from app.recommendations.domain.entities.discovery_session import SwipeAction
from app.recommendations.domain.exceptions import RecommendedRecipeNotFoundError
from app.recommendations.domain.repositories.discovery_session_repository import DiscoverySessionRepository
from app.recommendations.domain.services.compatibility_scorer import Compatibility, CompatibilityScorer
from app.recommendations.domain.services.ports import (
    CandidateRankingRequest,
    CandidateRecipe,
    FavoritesGateway,
    KitchenCatalog,
    RecipeCandidateSource,
)
from app.shared.application.pagination import Page


class GetRecommendationDeckUseCase:
    def __init__(
        self,
        session_repository: DiscoverySessionRepository,
        recipe_source: RecipeCandidateSource,
        kitchen: KitchenCatalog,
        favorites: FavoritesGateway,
        scorer: CompatibilityScorer,
    ) -> None:
        self._session_repository = session_repository
        self._recipe_source = recipe_source
        self._kitchen = kitchen
        self._favorites = favorites
        self._scorer = scorer

    async def execute(self, user_id: str, session_id: str, limit: int = 10, offset: int = 0) -> Page[RecommendationDTO]:
        session = await load_owned_session(self._session_repository, session_id, user_id)
        available_equipment = await self._kitchen.user_equipment_ids(user_id)

        ranking = await self._recipe_source.rank(
            CandidateRankingRequest(
                viewer_user_id=user_id,
                ingredient_ids=session.ingredient_ids,
                equipment_ids=available_equipment,
                ingredient_weight=self._scorer.ingredient_weight,
                equipment_weight=self._scorer.equipment_weight,
                min_ingredient_score=session.min_score,
                excluded_recipe_ids=sorted(session.swiped_recipe_ids),
                category_id=session.category_id,
                tag_ids=session.tag_ids,
                limit=limit,
                offset=offset,
            )
        )
        recipes = await self._recipe_source.get_many_visible(ranking.recipe_ids, user_id)
        page = [
            (
                recipe,
                self._scorer.score(
                    recipe.ingredient_ids,
                    recipe.equipment_ids,
                    set(session.ingredient_ids),
                    set(available_equipment),
                ),
            )
            for recipe in recipes
        ]
        return Page(items=await self._to_dtos(user_id, page), total=ranking.total, limit=limit, offset=offset)

    async def _to_dtos(
        self, user_id: str, page: list[tuple[CandidateRecipe, Compatibility]]
    ) -> list[RecommendationDTO]:
        ingredient_ids = {i for _, c in page for i in c.matched_ingredient_ids | c.missing_ingredient_ids}
        equipment_ids = {e for _, c in page for e in c.missing_equipment_ids}
        ingredient_names = await self._kitchen.ingredient_names(list(ingredient_ids))
        equipment_names = await self._kitchen.equipment_names(list(equipment_ids))
        saved = await self._favorites.saved_among(user_id, [recipe.id for recipe, _ in page])

        def refs(ids: frozenset[str], names: dict) -> list[NamedRefDTO]:
            return sorted(
                (NamedRefDTO(id=item_id, name=names[item_id]) for item_id in ids if item_id in names),
                # By the name as originally written: the viewer's language is unknown here.
                key=lambda ref: str(ref.name).lower(),
            )

        return [
            RecommendationDTO(
                recipe_id=recipe.id,
                title=recipe.title,
                description=recipe.description,
                cover_photo_url=recipe.cover_photo_url,
                category_name=recipe.category_name,
                difficulty_name=recipe.difficulty_name,
                tags=list(recipe.tag_names),
                prep_time_minutes=recipe.prep_time_minutes,
                servings=recipe.servings,
                is_own=recipe.created_by_user_id == user_id,
                is_personalization=recipe.is_personalization,
                source_recipe_title=recipe.source_recipe_title,
                compatibility_score=compatibility.ingredient_score,
                equipment_score=compatibility.equipment_score,
                rank_score=compatibility.rank_score,
                matched_ingredients=refs(compatibility.matched_ingredient_ids, ingredient_names),
                missing_ingredients=refs(compatibility.missing_ingredient_ids, ingredient_names),
                missing_equipment=refs(compatibility.missing_equipment_ids, equipment_names),
                has_all_equipment=compatibility.has_all_equipment,
                is_saved=recipe.id in saved,
            )
            for recipe, compatibility in page
        ]


class SwipeRecipeUseCase:
    """Records a swipe. Swiping right ('saved') also adds the recipe to the user's favorites.

    Saving one of the user's own recipes is rejected by portfolio (they are
    already part of the portfolio); the deck flags those cards with `is_own`
    so the client can hide the save action.
    """

    def __init__(
        self,
        session_repository: DiscoverySessionRepository,
        recipe_source: RecipeCandidateSource,
        kitchen: KitchenCatalog,
        favorites: FavoritesGateway,
        scorer: CompatibilityScorer,
    ) -> None:
        self._session_repository = session_repository
        self._recipe_source = recipe_source
        self._kitchen = kitchen
        self._favorites = favorites
        self._scorer = scorer

    async def execute(self, user_id: str, session_id: str, recipe_id: str, action: str) -> SwipeDTO:
        session = await load_owned_session(self._session_repository, session_id, user_id)
        recipe = await self._recipe_source.get_visible(recipe_id, user_id)
        if recipe is None:
            raise RecommendedRecipeNotFoundError(recipe_id)

        compatibility = self._scorer.score(
            recipe.ingredient_ids,
            recipe.equipment_ids,
            set(session.ingredient_ids),
            set(await self._kitchen.user_equipment_ids(user_id)),
        )
        swipe = session.swipe(recipe.id, SwipeAction(action), compatibility.ingredient_score)
        if swipe.action == SwipeAction.SAVED:
            await self._favorites.save(user_id, recipe.id)

        await self._session_repository.update(session)
        return swipe_to_dto(swipe)
