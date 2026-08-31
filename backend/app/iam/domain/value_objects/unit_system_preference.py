"""
UnitSystemPreference value object.

Mirrors the `preferred_unit_system` decision from the data model: a global,
per-user display preference ('metric' vs 'us') used later by the
measurement converter and recipe rendering. It never changes the values
actually stored for a recipe's ingredients — only how they are displayed.
"""
from __future__ import annotations

from enum import Enum


class UnitSystemPreference(str, Enum):
    METRIC = "metric"
    US = "us"
