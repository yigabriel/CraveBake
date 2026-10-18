"""
UserEquipment — one item of equipment the user has in their kitchen.

The equipment counterpart of the pantry: recommendations use it to rank
higher the recipes the user can actually make with what they own.
`user_id` is the opaque id minted by IAM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.equipment.domain.value_objects.equipment_id import EquipmentId
from app.equipment.domain.value_objects.user_equipment_id import UserEquipmentId
from app.shared.exceptions.domain_exceptions import ValidationError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserEquipment:
    id: UserEquipmentId
    user_id: str
    equipment_id: EquipmentId
    quantity: int = 1
    notes: str | None = None
    updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _validate_quantity(self.quantity)

    @classmethod
    def register(
        cls, user_id: str, equipment_id: EquipmentId, quantity: int = 1, notes: str | None = None
    ) -> "UserEquipment":
        return cls(
            id=UserEquipmentId(),
            user_id=user_id,
            equipment_id=equipment_id,
            quantity=quantity,
            notes=(notes or "").strip() or None,
        )

    def update(self, quantity: int, notes: str | None) -> None:
        _validate_quantity(quantity)
        self.quantity = quantity
        self.notes = (notes or "").strip() or None
        self.updated_at = _utc_now()


def _validate_quantity(quantity: int) -> None:
    if quantity < 1:
        raise ValidationError("Equipment quantity must be at least 1")
