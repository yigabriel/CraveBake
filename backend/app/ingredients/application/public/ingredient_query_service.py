"""
IngredientQueryService — the ingredients module's public read API (Open Host Service).

This is the only entry point other bounded contexts may use to read
ingredients and units. They receive the module's own DTOs (its published
language) and translate them in their own anti-corruption layer, so the
ingredients schema can change without breaking anyone as long as this
contract holds.
"""
from __future__ import annotations

from app.ingredients.application.dto.display_quantity_dto import DisplayQuantityDTO, QuantityToDisplayDTO
from app.ingredients.application.dto.ingredient_dto import IngredientDTO
from app.ingredients.application.dto.unit_dto import UnitDTO
from app.ingredients.application.mappers.ingredient_mapper import ingredient_to_dto
from app.ingredients.application.mappers.unit_mapper import unit_to_dto
from app.ingredients.domain.entities.unit import UnitSystem
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository
from app.ingredients.domain.repositories.ingredient_unit_conversion_repository import (
    IngredientUnitConversionRepository,
)
from app.ingredients.domain.repositories.unit_repository import UnitRepository
from app.ingredients.domain.repositories.user_ingredient_repository import UserIngredientRepository
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.services.unit_system_converter import UnitSystemConverter
from app.ingredients.domain.value_objects.unit_id import UnitId


class IngredientQueryService:
    def __init__(
        self,
        ingredient_repository: IngredientRepository,
        unit_repository: UnitRepository,
        user_ingredient_repository: UserIngredientRepository,
        conversion_repository: IngredientUnitConversionRepository,
        unit_system_converter: UnitSystemConverter,
    ) -> None:
        self._conversion_repository = conversion_repository
        self._unit_system_converter = unit_system_converter
        self._ingredient_repository = ingredient_repository
        self._unit_repository = unit_repository
        self._user_ingredient_repository = user_ingredient_repository

    async def get_ingredients(self, ids: list[str]) -> list[IngredientDTO]:
        """Ingredients that exist among `ids`; unknown or malformed ids are skipped."""
        parsed = _parse_ids(IngredientId, ids)
        return [ingredient_to_dto(item) for item in await self._ingredient_repository.get_many_by_ids(parsed)]

    async def get_units(self, ids: list[str]) -> list[UnitDTO]:
        """Units that exist among `ids`; unknown or malformed ids are skipped."""
        parsed = _parse_ids(UnitId, ids)
        return [unit_to_dto(unit) for unit in await self._unit_repository.get_many_by_ids(parsed)]


    async def list_pantry_ingredient_ids(self, user_id: str) -> list[str]:
        """Ids of the ingredients the user has registered in their pantry (quantities are not exposed)."""
        return [str(item.ingredient_id) for item in await self._user_ingredient_repository.list_by_user(user_id)]


    async def display_in_unit_system(
        self, items: list[QuantityToDisplayDTO], unit_system: str
    ) -> list[DisplayQuantityDTO]:
        """Each quantity expressed in `unit_system` ('metric' | 'us'), in the same order (display only).

        Unknown units are returned untouched with `converted=False`.
        """
        target = UnitSystem(unit_system)
        units = await self._unit_repository.list_all()
        units_by_id = {unit.id: unit for unit in units}
        units_by_abbreviation = {unit.abbreviation: unit for unit in units}
        ingredient_ids = _parse_ids(IngredientId, [item.ingredient_id for item in items])
        grams_per_unit: dict = {}
        for conversion in await self._conversion_repository.list_by_ingredients(ingredient_ids):
            grams_per_unit.setdefault(str(conversion.ingredient_id), {})[conversion.unit_id] = conversion.grams_equivalent

        result: list[DisplayQuantityDTO] = []
        for item in items:
            unit_id = UnitId.try_from_string(item.unit_id)
            unit = units_by_id.get(unit_id) if unit_id else None
            if unit is None:
                result.append(DisplayQuantityDTO(item.quantity, item.unit_id, "", converted=False))
                continue
            shown = self._unit_system_converter.to_system(
                item.quantity, unit, target, units_by_abbreviation, grams_per_unit.get(_canonical(item.ingredient_id), {})
            )
            result.append(
                DisplayQuantityDTO(shown.quantity, str(shown.unit.id), shown.unit.abbreviation, shown.converted)
            )
        return result


def _parse_ids(id_type, raw_ids: list[str]) -> list:
    return list({parsed for raw in raw_ids if (parsed := id_type.try_from_string(raw)) is not None})


def _canonical(raw_id: str) -> str:
    parsed = IngredientId.try_from_string(raw_id)
    return str(parsed) if parsed else raw_id
