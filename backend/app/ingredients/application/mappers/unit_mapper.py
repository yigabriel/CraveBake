"""Maps the Unit domain entity to UnitDTO."""
from app.ingredients.application.dto.unit_dto import UnitDTO
from app.ingredients.domain.entities.unit import Unit


def unit_to_dto(unit: Unit) -> UnitDTO:
    return UnitDTO(
        id=str(unit.id),
        name=unit.name,
        abbreviation=unit.abbreviation,
        unit_type=unit.unit_type.value,
        base_factor=unit.base_factor,
        unit_system=unit.unit_system.value,
    )
