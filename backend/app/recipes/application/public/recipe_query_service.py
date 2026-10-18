"""
RecipeQueryService — the recipes module's public read API (Open Host Service).

The only entry point other bounded contexts (portfolio, recommendations, and
later preparation) may use to read recipes. It speaks the module's published
language (`RecipeSummaryDTO`, `RecipeCompositionDTO`, ...) and applies the
recipes visibility rule itself, so no consumer has to know what "visible"
means (deleted, private, owned...) or how recipes are stored.
"""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import (
    IngredientOverlapQueryDTO,
    RankedRecipesDTO,
    RecipeCategoryDTO,
    RecipeCompositionDTO,
    RecipeDetailDTO,
    RecipeSummaryDTO,
    RecipeTagDTO,
)
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler, category_to_dto, tag_to_dto
from app.recipes.domain.entities.recipe import Recipe
from app.recipes.domain.repositories.recipe_catalog_repositories import (
    RecipeCategoryRepository,
    RecipeTagRepository,
)
from app.recipes.domain.repositories.recipe_repository import IngredientOverlapQuery, RecipeRepository
from app.recipes.domain.value_objects.recipe_category_id import RecipeCategoryId
from app.recipes.domain.value_objects.recipe_id import RecipeId
from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId


class RecipeQueryService:
    def __init__(
        self,
        recipe_repository: RecipeRepository,
        assembler: RecipeAssembler,
        category_repository: RecipeCategoryRepository,
        tag_repository: RecipeTagRepository,
    ) -> None:
        self._recipe_repository = recipe_repository
        self._assembler = assembler
        self._category_repository = category_repository
        self._tag_repository = tag_repository

    # --- Cards -----------------------------------------------------------------------

    async def get_visible(self, recipe_id: str, viewer_user_id: str) -> RecipeSummaryDTO | None:
        """The recipe if `viewer_user_id` may see it; None if it does not exist, is deleted or private."""
        summaries = await self.get_many_visible([recipe_id], viewer_user_id)
        return summaries[0] if summaries else None

    async def get_many_visible(self, recipe_ids: list[str], viewer_user_id: str) -> list[RecipeSummaryDTO]:
        """The recipes among `recipe_ids` that `viewer_user_id` may see; the rest are silently left out."""
        recipes = await self._visible_recipes(recipe_ids, viewer_user_id)
        return await self._assembler.to_summaries(recipes, viewer_user_id)

    async def get_detail(self, recipe_id: str, viewer_user_id: str) -> RecipeDetailDTO | None:
        """Full recipe (ingredients, equipment, steps, photos) if the viewer may see it; None otherwise."""
        recipes = await self._visible_recipes([recipe_id], viewer_user_id)
        return await self._assembler.to_detail(recipes[0], viewer_user_id) if recipes else None

    async def list_owned_by(self, user_id: str) -> list[RecipeSummaryDTO]:
        """Every non-deleted recipe the user created (originals and personalizations), newest first."""
        page = await self._recipe_repository.list_by_owner(user_id)
        return await self._assembler.to_summaries(page.items, user_id)

    # --- Compositions (what a recipe is made with) ------------------------------------

    async def rank_by_ingredient_overlap(self, query: IngredientOverlapQueryDTO) -> RankedRecipesDTO:
        """Recipe ids the viewer can cook, best first; scored and paginated by the database.

        Malformed category/tag ids match nothing; malformed recipe ids to exclude are ignored.
        """
        category_id = RecipeCategoryId.try_from_string(query.category_id) if query.category_id else None
        tag_ids = [parsed for raw in query.tag_ids if (parsed := RecipeTagId.try_from_string(raw))]
        if (query.category_id and category_id is None) or len(tag_ids) != len(query.tag_ids):
            return RankedRecipesDTO(recipe_ids=[], total=0)

        ranked = await self._recipe_repository.rank_by_ingredient_overlap(
            IngredientOverlapQuery(
                viewer_user_id=query.viewer_user_id,
                ingredient_ids=query.ingredient_ids,
                equipment_ids=query.equipment_ids,
                ingredient_weight=query.ingredient_weight,
                equipment_weight=query.equipment_weight,
                min_ingredient_score=query.min_ingredient_score,
                excluded_recipe_ids=[
                    parsed for raw in query.excluded_recipe_ids if (parsed := RecipeId.try_from_string(raw))
                ],
                category_id=category_id,
                tag_ids=tag_ids,
                limit=query.limit,
                offset=query.offset,
            )
        )
        return RankedRecipesDTO(recipe_ids=[str(recipe_id) for recipe_id in ranked.recipe_ids], total=ranked.total)

    async def get_compositions(self, recipe_ids: list[str], viewer_user_id: str) -> list[RecipeCompositionDTO]:
        """Compositions of the visible recipes among `recipe_ids`, in the order the ids were given."""
        recipes = await self._visible_recipes(recipe_ids, viewer_user_id)
        summaries = await self._assembler.to_summaries(recipes, viewer_user_id)
        compositions = {
            str(recipe.id): RecipeCompositionDTO(
                recipe=summary,
                ingredient_ids=sorted({line.ingredient_id for line in recipe.ingredients}),
                equipment_ids=sorted({item.equipment_id for item in recipe.equipment}),
            )
            for recipe, summary in zip(recipes, summaries)
        }
        return [compositions[recipe_id] for recipe_id in dict.fromkeys(recipe_ids) if recipe_id in compositions]

    async def get_composition(self, recipe_id: str, viewer_user_id: str) -> RecipeCompositionDTO | None:
        """The composition of a recipe the viewer may see; None otherwise."""
        compositions = await self.get_compositions([recipe_id], viewer_user_id)
        return compositions[0] if compositions else None

    # --- Taxonomy -----------------------------------------------------------------------

    async def list_categories(self) -> list[RecipeCategoryDTO]:
        return [category_to_dto(category) for category in await self._category_repository.list_all()]

    async def list_tags(self) -> list[RecipeTagDTO]:
        return [tag_to_dto(tag) for tag in await self._tag_repository.list_all()]

    async def _visible_recipes(self, recipe_ids: list[str], viewer_user_id: str) -> list[Recipe]:
        parsed = list({parsed for raw in recipe_ids if (parsed := RecipeId.try_from_string(raw)) is not None})
        return [
            recipe
            for recipe in await self._recipe_repository.get_many_by_ids(parsed)
            if recipe.is_visible_to(viewer_user_id)
        ]
