"""Input DTO for UpdateUserUseCase."""
from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateUserDTO:
    full_name: str | None = None
    avatar_url: str | None = None

