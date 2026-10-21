"""Pydantic schemas for the equipment endpoints."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints
from app.shared.presentation.i18n import LocalizedStr

EquipmentTypeLiteral = Literal["mold", "utensil", "appliance", "other"]


class CreateEquipmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    equipment_type: EquipmentTypeLiteral
    description: str | None = Field(default=None, max_length=1024)
    translations: dict[Literal["es", "en"], Annotated[str, StringConstraints(max_length=150)]] = Field(
        default_factory=dict,
        description="The name in the other languages, as reviewed by the user (blank = not translated)",
    )


class EquipmentResponse(BaseModel):
    id: str
    name: LocalizedStr
    equipment_type: str
    description: str | None


class UpsertUserEquipmentRequest(BaseModel):
    equipment_id: str
    quantity: int = Field(default=1, ge=1)
    notes: str | None = Field(default=None, max_length=500)


class UserEquipmentResponse(BaseModel):
    id: str
    equipment: EquipmentResponse
    quantity: int
    notes: str | None
    updated_at: datetime
