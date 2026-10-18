"""
ConvertMeasurementUseCase — backs the "Herramientas > conversor de medidas".

Fetches the involved units (and, when needed, the ingredient-specific
volume<->weight ratio) and delegates the actual math to the
`MeasurementConverter` domain service.
"""
from __future__ import annotations

from app.ingredients.application.dto.convert_measurement_dto import (
    ConversionResultDTO,
    ConvertMeasurementDTO,
)
from app.ingredients.application.mappers.unit_mapper import unit_to_dto
from app.ingredients.domain.entities.ingredient_unit_conversion import IngredientUnitConversion
from app.ingredients.domain.entities.unit import Unit, UnitType
from app.ingredients.domain.exceptions import UnitNotFoundError
from app.ingredients.domain.repositories.ingredient_unit_conversion_repository import (
    IngredientUnitConversionRepository,
)
from app.ingredients.domain.repositories.unit_repository import UnitRepository
from app.ingredients.domain.services.measurement_converter import MeasurementConverter
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.value_objects.unit_id import UnitId


class ConvertMeasurementUseCase:
    def __init__(
        self,
        unit_repository: UnitRepository,
        ingredient_unit_conversion_repository: IngredientUnitConversionRepository,
        measurement_converter: MeasurementConverter,
    ) -> None:
        self._unit_repository = unit_repository
        self._ingredient_unit_conversion_repository = ingredient_unit_conversion_repository
        self._measurement_converter = measurement_converter

    async def execute(self, dto: ConvertMeasurementDTO) -> ConversionResultDTO:
        from_unit = await self._get_unit(dto.from_unit_id)
        to_unit = await self._get_unit(dto.to_unit_id)

        ingredient_conversion, conversion_unit = None, None
        ingredient_id = IngredientId.try_from_string(dto.ingredient_id) if dto.ingredient_id else None
        if ingredient_id is not None and from_unit.unit_type != to_unit.unit_type:
            volume_unit = from_unit if from_unit.unit_type == UnitType.VOLUME else to_unit
            ingredient_conversion, conversion_unit = await self._best_conversion(ingredient_id, volume_unit)

        converted = self._measurement_converter.convert(
            quantity=dto.quantity,
            from_unit=from_unit,
            to_unit=to_unit,
            ingredient_conversion=ingredient_conversion,
            conversion_unit=conversion_unit,
        )

        return ConversionResultDTO(
            original_quantity=dto.quantity,
            from_unit=unit_to_dto(from_unit),
            to_unit=unit_to_dto(to_unit),
            converted_quantity=converted,
        )

    async def _best_conversion(
        self, ingredient_id: IngredientId, volume_unit: Unit
    ) -> tuple[IngredientUnitConversion | None, Unit | None]:
        """The ingredient's figure for `volume_unit` itself, else the one of its biggest known measure.

        The exact figure wins because measures are not always proportional
        (a tbsp of butter is not cup/16). Otherwise the biggest measure is the
        most precise one to derive ml/l from (1 cup of flour -> 125 g).
        """
        exact = await self._ingredient_unit_conversion_repository.get_by_ingredient_and_unit(
            ingredient_id, volume_unit.id
        )
        if exact is not None:
            return exact, volume_unit

        conversions = await self._ingredient_unit_conversion_repository.list_by_ingredients([ingredient_id])
        units = {unit.id: unit for unit in await self._unit_repository.get_many_by_ids([c.unit_id for c in conversions])}
        candidates = [(units[c.unit_id], c) for c in conversions if c.unit_id in units]
        if not candidates:
            return None, None
        unit, conversion = max(candidates, key=lambda pair: pair[0].base_factor)
        return conversion, unit

    async def _get_unit(self, raw_id: str) -> Unit:
        unit_id = UnitId.try_from_string(raw_id)
        unit = await self._unit_repository.get_by_id(unit_id) if unit_id else None
        if unit is None:
            raise UnitNotFoundError(raw_id)
        return unit
