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
        from_unit = await self._unit_repository.get_by_id(UnitId.from_string(dto.from_unit_id))
        if from_unit is None:
            raise UnitNotFoundError(dto.from_unit_id)

        to_unit = await self._unit_repository.get_by_id(UnitId.from_string(dto.to_unit_id))
        if to_unit is None:
            raise UnitNotFoundError(dto.to_unit_id)

        ingredient_conversion = None
        if dto.ingredient_id is not None and from_unit.unit_type != to_unit.unit_type:
            volume_unit_id = from_unit.id if from_unit.unit_type.value == "volume" else to_unit.id
            ingredient_conversion = await self._ingredient_unit_conversion_repository.get_by_ingredient_and_unit(
                IngredientId.from_string(dto.ingredient_id), volume_unit_id
            )

        converted = self._measurement_converter.convert(
            quantity=dto.quantity,
            from_unit=from_unit,
            to_unit=to_unit,
            ingredient_conversion=ingredient_conversion,
        )

        return ConversionResultDTO(
            original_quantity=dto.quantity,
            from_unit=unit_to_dto(from_unit),
            to_unit=unit_to_dto(to_unit),
            converted_quantity=converted,
        )
