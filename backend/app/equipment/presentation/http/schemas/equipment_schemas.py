"""Pydantic schemas for the equipment endpoints."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EquipmentTypeLiteral = Literal["molde", "utensilio", "electrodomestico", "otro"]


class CreateEquipmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    equipment_type: EquipmentTypeLiteral
    description: str | None = Field(default=None, max_length=1024)


class EquipmentResponse(BaseModel):
    id: str
    name: str
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
