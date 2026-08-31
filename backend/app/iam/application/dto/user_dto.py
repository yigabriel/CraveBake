"""Output DTO"""
from dataclasses import dataclass

# Hace el DTO inmutable: una vez creado, no se pueden modificar sus campos.
@dataclass(frozen=True)
class UserDTO:
    id: str
    email: str
    full_name: str
    avatar_url: str | None
    preferred_unit_system: str
    preferred_language: str
    is_active: bool
