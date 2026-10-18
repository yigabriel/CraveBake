"""
UnitSystemPreference value object.

Mirrors the `preferred_unit_system` decision from the data model: a global,
per-user display preference ('metric' vs 'us') used later by the
measurement converter and recipe rendering. It never changes the values
actually stored for a recipe's ingredients — only how they are displayed.
"""
from __future__ import annotations

from enum import Enum

from app.shared.exceptions.domain_exceptions import ValidationError


class UnitSystemPreference(str, Enum):
    METRIC = "metric"
    US = "us"

    @classmethod
    def _missing_(cls, value: object) -> None:
        # Unknown values become a 400 instead of a bare ValueError (500).
        allowed = ", ".join(member.value for member in cls)
        raise ValidationError(f"'{value}' is not a valid unit system. Allowed: {allowed}")
