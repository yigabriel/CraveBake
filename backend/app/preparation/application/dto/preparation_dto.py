"""DTOs for the preparation bounded context."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.shared.domain.value_objects.localized_text import LocalizedText


@dataclass(frozen=True)
class PreparedIngredientDTO:
    ingredient_id: str
    ingredient_name: LocalizedText | None
    quantity: Decimal  # in the requested unit system
    unit_abbreviation: str | None
    original_quantity: Decimal  # as the recipe was written
    original_unit_abbreviation: str | None
    converted: bool
    notes: str | None


@dataclass(frozen=True)
class PreparedStepDTO:
    step_number: int
    title: str | None
    instructions: str
    photo_url: str | None
    timer_seconds: int | None
    timer_started_at: datetime | None
    timer_remaining_seconds: int | None
    is_completed: bool
    completed_at: datetime | None
    is_current: bool


@dataclass(frozen=True)
class PreparationDetailDTO:
    id: str
    recipe_id: str
    recipe_title: str
    cover_photo_url: str | None
    servings: int | None
    status: str
    unit_system: str  # what the quantities are shown in: metric | us | original
    current_step_number: int | None
    completed_steps: int
    total_steps: int
    ingredients: list[PreparedIngredientDTO]
    steps: list[PreparedStepDTO]
    started_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True)
class PreparationSummaryDTO:
    id: str
    recipe_id: str
    recipe_title: str
    cover_photo_url: str | None
    status: str
    completed_steps: int
    total_steps: int
    started_at: datetime
    finished_at: datetime | None
