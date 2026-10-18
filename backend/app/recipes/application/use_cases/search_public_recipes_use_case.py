"""
SearchPublicRecipesUseCase — powers "Explorar".

Only public, non-deleted recipes. Filters by text, category, difficulty,
maximum preparation time, ingredients and tags (the recipe must have all of
the given ingredients and all of the given tags).
Filter ids that are malformed simply match nothing.
"""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import RecipeSummaryDTO, SearchRecipesDTO
from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.domain.repositories.recipe_repository import RecipeRepository, RecipeSearchCriteria
from app.recipes.domain.value_objects.difficulty_id import DifficultyId
from app.recipes.domain.value_objects.recipe_category_id import RecipeCategoryId
from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId
from app.shared.application.pagination import Page
from app.shared.domain.value_objects.entity_id import EntityId


class SearchPublicRecipesUseCase:
    def __init__(self, recipe_repository: RecipeRepository, assembler: RecipeAssembler) -> None:
        self._recipe_repository = recipe_repository
        self._assembler = assembler

    async def execute(self, dto: SearchRecipesDTO, viewer_user_id: str) -> Page[RecipeSummaryDTO]:
        category_id = RecipeCategoryId.try_from_string(dto.category_id) if dto.category_id else None
        difficulty_id = DifficultyId.try_from_string(dto.difficulty_id) if dto.difficulty_id else None
        # Canonical form, as stored by RecipeReferenceValidator ("ABC-..." and "abc-..." are the same id).
        ingredient_ids = [str(parsed) for raw in dto.ingredient_ids if (parsed := EntityId.try_from_string(raw))]
        tag_ids = [parsed for raw in dto.tag_ids if (parsed := RecipeTagId.try_from_string(raw))]

        if (
            (dto.category_id and category_id is None)
            or (dto.difficulty_id and difficulty_id is None)
            or len(ingredient_ids) != len(dto.ingredient_ids)
            or len(tag_ids) != len(dto.tag_ids)
        ):
            return Page(items=[], total=0, limit=dto.limit, offset=dto.offset)

        page = await self._recipe_repository.search_public(
            RecipeSearchCriteria(
                query=dto.query.strip() if dto.query else None,
                category_id=category_id,
                difficulty_id=difficulty_id,
                max_prep_time_minutes=dto.max_prep_time_minutes,
                ingredient_ids=ingredient_ids,
                tag_ids=tag_ids,
                limit=dto.limit,
                offset=dto.offset,
            )
        )
        return Page(
            items=await self._assembler.to_summaries(page.items, viewer_user_id),
            total=page.total,
            limit=dto.limit,
            offset=dto.offset,
        )
