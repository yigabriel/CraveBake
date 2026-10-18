"""
LanguagePreference value object.
Represents a user's preferred language for the application interface. This value object is used to store and manage the user's language preference, which can be utilized throughout the application to provide localized content and user experience.
The preferred language is typically represented as a string (e.g., 'en' for English,
"""
from __future__ import annotations

from enum import Enum

from app.shared.exceptions.domain_exceptions import ValidationError


class LanguagePreference(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"

    @classmethod
    def _missing_(cls, value: object) -> None:
        # Unknown values become a 400 instead of a bare ValueError (500).
        allowed = ", ".join(member.value for member in cls)
        raise ValidationError(f"'{value}' is not a valid language. Allowed: {allowed}")
