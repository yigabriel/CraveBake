"""Read-only catalog use cases: recipe categories, difficulty levels and tags."""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import DifficultyDTO, RecipeCategoryDTO, RecipeTagDTO
from app.recipes.application.mappers.recipe_assembler import category_to_dto, difficulty_to_dto, tag_to_dto
from app.recipes.domain.entities.recipe_tag import TagGroup
from app.recipes.domain.repositories.recipe_catalog_repositories import (
    DifficultyRepository,
    RecipeCategoryRepository,
    RecipeTagRepository,
)


class ListRecipeCategoriesUseCase:
    def __init__(self, category_repository: RecipeCategoryRepository) -> None:
        self._category_repository = category_repository

    async def execute(self) -> list[RecipeCategoryDTO]:
        return [category_to_dto(category) for category in await self._category_repository.list_all()]


class ListDifficultiesUseCase:
    def __init__(self, difficulty_repository: DifficultyRepository) -> None:
        self._difficulty_repository = difficulty_repository

    async def execute(self) -> list[DifficultyDTO]:
        return [difficulty_to_dto(difficulty) for difficulty in await self._difficulty_repository.list_all()]


class ListRecipeTagsUseCase:
    """Every tag, grouped (in `TagGroup` order) and alphabetical inside each group; optionally one group only."""

    def __init__(self, tag_repository: RecipeTagRepository) -> None:
        self._tag_repository = tag_repository

    async def execute(self, group: str | None = None) -> list[RecipeTagDTO]:
        group_order = {tag_group: index for index, tag_group in enumerate(TagGroup)}
        tags = [tag for tag in await self._tag_repository.list_all() if group is None or tag.group.value == group]
        tags.sort(key=lambda tag: (group_order[tag.group], tag.name.lower()))
        return [tag_to_dto(tag) for tag in tags]
