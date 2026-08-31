"""
LanguagePreference value object.
Represents a user's preferred language for the application interface. This value object is used to store and manage the user's language preference, which can be utilized throughout the application to provide localized content and user experience.
The preferred language is typically represented as a string (e.g., 'en' for English,
"""
from __future__ import annotations

from enum import Enum


class LanguagePreference(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"