"""
RecipeStep — one step of the guided preparation mode.

`step_number` is assigned by the `Recipe` aggregate (1..n, in order), so it is
always unique and gap-free within a recipe.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.recipes.domain.value_objects.recipe_step_id import RecipeStepId
from app.shared.exceptions.domain_exceptions import ValidationError


@dataclass
class RecipeStep:
    id: RecipeStepId
    step_number: int
    instructions: str
    title: str | None = None
    timer_seconds: int | None = None

    def __post_init__(self) -> None:
        self.instructions = (self.instructions or "").strip()
        if not self.instructions:
            raise ValidationError("Step instructions cannot be empty")
        if self.title is not None:
            self.title = self.title.strip() or None
        if self.timer_seconds is not None and self.timer_seconds <= 0:
            raise ValidationError("Step timer must be greater than zero seconds")
