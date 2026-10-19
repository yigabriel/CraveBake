"""Pydantic schemas for the preparation endpoints."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.shared.presentation.i18n import LocalizedStr

UnitSystemLiteral = Literal["metric", "us", "original"]
PreparationStatusLiteral = Literal["in_progress", "completed", "abandoned"]


class StartPreparationRequest(BaseModel):
    recipe_id: str


class GoToStepRequest(BaseModel):
    step_number: int = Field(ge=1)


class PreparedIngredientResponse(BaseModel):
    ingredient_id: str
    ingredient_name: LocalizedStr | None
    quantity: Decimal = Field(description="In the requested unit system")
    unit_abbreviation: str | None
    original_quantity: Decimal = Field(description="As the recipe was written")
    original_unit_abbreviation: str | None
    converted: bool
    notes: str | None


class PreparedStepResponse(BaseModel):
    step_number: int
    title: str | None
    instructions: str
    photo_url: str | None
    timer_seconds: int | None
    timer_started_at: datetime | None
    timer_remaining_seconds: int | None = Field(description="Seconds left on a started timer; 0 when it has rung")
    is_completed: bool
    completed_at: datetime | None
    is_current: bool


class PreparationDetailResponse(BaseModel):
    id: str
    recipe_id: str
    recipe_title: str
    cover_photo_url: str | None
    servings: int | None
    status: str  # in_progress | completed | abandoned
    unit_system: str  # metric | us | original
    current_step_number: int | None
    completed_steps: int
    total_steps: int
    ingredients: list[PreparedIngredientResponse]
    steps: list[PreparedStepResponse]
    started_at: datetime
    finished_at: datetime | None


class PreparationSummaryResponse(BaseModel):
    id: str
    recipe_id: str
    recipe_title: str
    cover_photo_url: str | None
    status: str
    completed_steps: int
    total_steps: int
    started_at: datetime
    finished_at: datetime | None
