"""
RecipeAssembler — turns Recipe aggregates into output DTOs.

Unlike the plain mapper functions of other modules, building a recipe DTO
needs lookups (category / difficulty names, ingredient names and unit
abbreviations from the ingredients context, the original of a
personalization), so this is a small class that batches those lookups once
per call instead of once per recipe.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.recipes.application.dto.recipe_dto import (
    DifficultyDTO,
    RecipeCategoryDTO,
    RecipeDetailDTO,
    RecipeEquipmentDTO,
    RecipeIngredientDTO,
    RecipePhotoDTO,
    RecipeStepDTO,
    RecipeSummaryDTO,
    RecipeTagDTO,
)
from app.recipes.domain.entities.difficulty import Difficulty
from app.recipes.domain.entities.recipe import Recipe
from app.recipes.domain.entities.recipe_category import RecipeCategory
from app.recipes.domain.entities.recipe_photo import RecipePhoto
from app.recipes.domain.entities.recipe_tag import RecipeTag
from app.recipes.domain.repositories.recipe_catalog_repositories import (
    DifficultyRepository,
    RecipeCategoryRepository,
    RecipeTagRepository,
)
from app.recipes.domain.repositories.recipe_repository import RecipeRepository
from app.recipes.domain.services.equipment_catalog import EquipmentCatalog
from app.recipes.domain.services.ingredient_catalog import DisplayedQuantity, IngredientCatalog, QuantityToDisplay
from app.recipes.domain.value_objects.recipe_id import RecipeId

ORIGINAL_UNITS = "original"


def category_to_dto(category: RecipeCategory) -> RecipeCategoryDTO:
    return RecipeCategoryDTO(id=str(category.id), name=category.name)


def difficulty_to_dto(difficulty: Difficulty) -> DifficultyDTO:
    return DifficultyDTO(id=str(difficulty.id), name=difficulty.name, level_order=difficulty.level_order)


def tag_to_dto(tag: RecipeTag) -> RecipeTagDTO:
    return RecipeTagDTO(id=str(tag.id), name=tag.name, group=tag.group.value, group_name=tag.group.label)


def photo_to_dto(photo: RecipePhoto) -> RecipePhotoDTO:
    return RecipePhotoDTO(
        id=str(photo.id),
        photo_type=photo.photo_type.value,
        photo_url=photo.photo_url,
        position=photo.position,
        step_id=str(photo.step_id) if photo.step_id else None,
    )


@dataclass(frozen=True)
class _Context:
    """Lookups shared by every recipe of one assembler call."""

    categories: dict
    difficulties: dict
    tags: dict
    sources: dict[RecipeId, Recipe]

    def common_fields(self, recipe: Recipe) -> dict:
        source = self.sources.get(recipe.source_recipe_id) if recipe.source_recipe_id else None
        return {
            "id": str(recipe.id),
            "title": recipe.title,
            "description": recipe.description,
            "category": self.categories.get(recipe.category_id) if recipe.category_id else None,
            "difficulty": self.difficulties.get(recipe.difficulty_id) if recipe.difficulty_id else None,
            "tags": sorted(
                (self.tags[tag_id] for tag_id in recipe.tag_ids if tag_id in self.tags),
                key=lambda tag: tag.name.lower(),
            ),
            "prep_time_minutes": recipe.prep_time_minutes,
            "servings": recipe.servings,
            "is_public": recipe.is_public,
            "is_personalization": recipe.is_personalization,
            "source_recipe_id": str(recipe.source_recipe_id) if recipe.source_recipe_id else None,
            "source_recipe_title": source.title if source else None,
            # The personalization is a snapshot taken at `created_at`; any later change to the original is news.
            "source_updated_since_personalized": source.updated_at > recipe.created_at if source else None,
            "created_by_user_id": recipe.created_by_user_id,
            "created_at": recipe.created_at,
            "updated_at": recipe.updated_at,
        }


class RecipeAssembler:
    def __init__(
        self,
        recipe_repository: RecipeRepository,
        category_repository: RecipeCategoryRepository,
        difficulty_repository: DifficultyRepository,
        ingredient_catalog: IngredientCatalog,
        equipment_catalog: EquipmentCatalog,
        tag_repository: RecipeTagRepository,
    ) -> None:
        self._tag_repository = tag_repository
        self._recipe_repository = recipe_repository
        self._category_repository = category_repository
        self._difficulty_repository = difficulty_repository
        self._ingredient_catalog = ingredient_catalog
        self._equipment_catalog = equipment_catalog

    async def to_summaries(self, recipes: list[Recipe], viewer_user_id: str) -> list[RecipeSummaryDTO]:
        context = await self._load_context(recipes, viewer_user_id)
        return [
            RecipeSummaryDTO(
                **context.common_fields(recipe),
                cover_photo_url=recipe.cover_photos[0].photo_url if recipe.cover_photos else None,
            )
            for recipe in recipes
        ]

    async def to_detail(
        self, recipe: Recipe, viewer_user_id: str, unit_system: str = ORIGINAL_UNITS
    ) -> RecipeDetailDTO:
        """`unit_system` only changes the display_* fields of the ingredients; the stored recipe is untouched."""
        context = await self._load_context([recipe], viewer_user_id)
        lines = sorted(recipe.ingredients, key=lambda line: line.position)
        ingredients = await self._ingredient_catalog.get_ingredients([line.ingredient_id for line in lines])
        units = await self._ingredient_catalog.get_units([line.unit_id for line in lines])
        equipment = await self._equipment_catalog.get_equipment([item.equipment_id for item in recipe.equipment])

        def abbreviation(line) -> str | None:
            return units[line.unit_id].abbreviation if line.unit_id in units else None

        if unit_system == ORIGINAL_UNITS:
            shown = [DisplayedQuantity(line.quantity, abbreviation(line) or "", converted=False) for line in lines]
        else:
            shown = await self._ingredient_catalog.display_in(
                [QuantityToDisplay(line.ingredient_id, line.quantity, line.unit_id) for line in lines], unit_system
            )

        return RecipeDetailDTO(
            **context.common_fields(recipe),
            video_url=recipe.video_url,
            is_owner=recipe.is_owned_by(viewer_user_id),
            cover_photos=[photo_to_dto(photo) for photo in recipe.cover_photos],
            ingredients=[
                RecipeIngredientDTO(
                    id=str(line.id),
                    ingredient_id=line.ingredient_id,
                    ingredient_name=ingredients[line.ingredient_id].name
                    if line.ingredient_id in ingredients
                    else None,
                    quantity=line.quantity,
                    unit_id=line.unit_id,
                    unit_abbreviation=abbreviation(line),
                    notes=line.notes,
                    position=line.position,
                    display_quantity=display.quantity,
                    display_unit_abbreviation=display.unit_abbreviation or abbreviation(line),
                    converted=display.converted,
                )
                for line, display in zip(lines, shown)
            ],
            equipment=[
                RecipeEquipmentDTO(
                    id=str(item.id),
                    equipment_id=item.equipment_id,
                    equipment_name=equipment[item.equipment_id].name if item.equipment_id in equipment else None,
                    notes=item.notes,
                )
                for item in recipe.equipment
            ],
            steps=[
                RecipeStepDTO(
                    id=str(step.id),
                    step_number=step.step_number,
                    title=step.title,
                    instructions=step.instructions,
                    timer_seconds=step.timer_seconds,
                    photo=photo_to_dto(photo) if (photo := recipe.photo_for_step(step.id)) else None,
                )
                for step in sorted(recipe.steps, key=lambda step: step.step_number)
            ],
            unit_system=unit_system,
        )

    async def _load_context(self, recipes: list[Recipe], viewer_user_id: str) -> _Context:
        # Both catalogs are tiny, seeded lists: loading them whole is cheaper than per-id lookups.
        categories = {category.id: category_to_dto(category) for category in await self._category_repository.list_all()}
        difficulties = {
            difficulty.id: difficulty_to_dto(difficulty) for difficulty in await self._difficulty_repository.list_all()
        }
        tags = {tag.id: tag_to_dto(tag) for tag in await self._tag_repository.list_all()}
        source_ids = list({recipe.source_recipe_id for recipe in recipes if recipe.source_recipe_id})
        # An original that was deleted or made private stays hidden, even from those who personalized it.
        sources = {
            source.id: source
            for source in await self._recipe_repository.get_many_by_ids(source_ids)
            if source.is_visible_to(viewer_user_id)
        }
        return _Context(categories=categories, difficulties=difficulties, tags=tags, sources=sources)
