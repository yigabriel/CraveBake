"""Input DTO for UpdateLanguageUseCase."""
from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateLanguageDTO:
    preferred_language: str
