"""Difficulty — catalog of difficulty levels; `level_order` sorts them from easiest to hardest."""
from __future__ import annotations

from dataclasses import dataclass

from app.recipes.domain.value_objects.difficulty_id import DifficultyId
from app.shared.domain.value_objects.localized_text import LocalizedText


@dataclass
class Difficulty:
    id: DifficultyId
    name: LocalizedText
    level_order: int
