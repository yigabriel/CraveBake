"""
RecipeReferenceValidator — checks that every id a recipe points to exists.

Category and difficulty live in this module; ingredients and units live in
the ingredients context and are checked through the `IngredientCatalog`
port; equipment lives in the equipment context (`EquipmentCatalog` port). Validating up front turns what would otherwise be a foreign-key error
(a 500) into a clean 404 naming the missing id.
"""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import RecipeEquipmentInputDTO, RecipeIngredientInputDTO
from app.recipes.domain.entities.recipe import EquipmentLine, IngredientLine
from app.recipes.domain.exceptions import (
    DifficultyNotFoundError,
    RecipeCategoryNotFoundError,
    RecipeTagNotFoundError,
    ReferencedEquipmentNotFoundError,
    ReferencedIngredientNotFoundError,
    ReferencedUnitNotFoundError,
)
from app.recipes.domain.repositories.recipe_catalog_repositories import (
    DifficultyRepository,
    RecipeCategoryRepository,
    RecipeTagRepository,
)
from app.recipes.domain.services.equipment_catalog import EquipmentCatalog
from app.recipes.domain.services.ingredient_catalog import IngredientCatalog
from app.recipes.domain.value_objects.difficulty_id import DifficultyId
from app.recipes.domain.value_objects.recipe_category_id import RecipeCategoryId
from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId
from app.shared.domain.value_objects.entity_id import EntityId


class RecipeReferenceValidator:
    def __init__(
        self,
        category_repository: RecipeCategoryRepository,
        difficulty_repository: DifficultyRepository,
        ingredient_catalog: IngredientCatalog,
        equipment_catalog: EquipmentCatalog,
        tag_repository: RecipeTagRepository,
    ) -> None:
        self._tag_repository = tag_repository
        self._category_repository = category_repository
        self._difficulty_repository = difficulty_repository
        self._ingredient_catalog = ingredient_catalog
        self._equipment_catalog = equipment_catalog

    async def category(self, raw_id: str | None) -> RecipeCategoryId | None:
        if raw_id is None:
            return None
        category_id = RecipeCategoryId.try_from_string(raw_id)
        if category_id is None or await self._category_repository.get_by_id(category_id) is None:
            raise RecipeCategoryNotFoundError(raw_id)
        return category_id

    async def difficulty(self, raw_id: str | None) -> DifficultyId | None:
        if raw_id is None:
            return None
        difficulty_id = DifficultyId.try_from_string(raw_id)
        if difficulty_id is None or await self._difficulty_repository.get_by_id(difficulty_id) is None:
            raise DifficultyNotFoundError(raw_id)
        return difficulty_id

    async def tags(self, raw_ids: list[str]) -> list[RecipeTagId]:
        parsed: list[RecipeTagId] = []
        for raw in raw_ids:
            tag_id = RecipeTagId.try_from_string(raw)
            if tag_id is None:
                raise RecipeTagNotFoundError(raw)
            parsed.append(tag_id)
        known = {tag.id for tag in await self._tag_repository.get_many_by_ids(list(set(parsed)))}
        for raw, tag_id in zip(raw_ids, parsed):
            if tag_id not in known:
                raise RecipeTagNotFoundError(raw)
        return parsed

    async def ingredient_lines(self, lines: list[RecipeIngredientInputDTO]) -> list[IngredientLine]:
        # Canonical form ("ABC-..." and "abc-..." are the same id), so lookups and storage agree.
        ingredient_ids = [_canonical(line.ingredient_id) for line in lines]
        unit_ids = [_canonical(line.unit_id) for line in lines]
        known_ingredients = await self._ingredient_catalog.get_ingredients(ingredient_ids)
        known_units = await self._ingredient_catalog.get_units(unit_ids)

        for line, ingredient_id in zip(lines, ingredient_ids):
            if ingredient_id not in known_ingredients:
                raise ReferencedIngredientNotFoundError(line.ingredient_id)
        for line, unit_id in zip(lines, unit_ids):
            if unit_id not in known_units:
                raise ReferencedUnitNotFoundError(line.unit_id)

        return [
            IngredientLine(
                ingredient_id=ingredient_id,
                quantity=line.quantity,
                unit_id=unit_id,
                notes=line.notes,
                section=line.section,
            )
            for line, ingredient_id, unit_id in zip(lines, ingredient_ids, unit_ids)
        ]


    async def equipment_lines(self, lines: list[RecipeEquipmentInputDTO]) -> list[EquipmentLine]:
        equipment_ids = [_canonical(line.equipment_id) for line in lines]
        known_equipment = await self._equipment_catalog.get_equipment(equipment_ids)
        for line, equipment_id in zip(lines, equipment_ids):
            if equipment_id not in known_equipment:
                raise ReferencedEquipmentNotFoundError(line.equipment_id)
        return [
            EquipmentLine(equipment_id=equipment_id, notes=line.notes)
            for line, equipment_id in zip(lines, equipment_ids)
        ]


def _canonical(raw_id: str) -> str:
    parsed = EntityId.try_from_string(raw_id)
    return str(parsed) if parsed else raw_id
