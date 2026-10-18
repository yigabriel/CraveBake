"""Maps equipment domain entities to DTOs."""
from app.equipment.application.dto.equipment_dto import EquipmentDTO, UserEquipmentDTO
from app.equipment.domain.entities.equipment import Equipment
from app.equipment.domain.entities.user_equipment import UserEquipment


def equipment_to_dto(equipment: Equipment) -> EquipmentDTO:
    return EquipmentDTO(
        id=str(equipment.id),
        name=equipment.name,
        equipment_type=equipment.equipment_type.value,
        description=equipment.description,
    )


def user_equipment_to_dto(item: UserEquipment, equipment: Equipment) -> UserEquipmentDTO:
    return UserEquipmentDTO(
        id=str(item.id),
        equipment=equipment_to_dto(equipment),
        quantity=item.quantity,
        notes=item.notes,
        updated_at=item.updated_at,
    )
