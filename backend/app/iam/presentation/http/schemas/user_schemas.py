"""Pydantic response model for a user, as exposed via the HTTP API."""
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: str | None
    preferred_unit_system: str
    preferred_language: str
    is_active: bool


class UpdateUnitPreferenceRequest(BaseModel):
    preferred_unit_system: str
