"""
PreparationSession — aggregate root of the guided cooking mode.

Starting a preparation *copies* the recipe (title, ingredients, steps,
timers, step photos). From then on the session is self-contained:

- Progress always points to steps that exist, because the steps are its own.
  If the author edits, reorders or deletes the recipe meanwhile, an ongoing
  preparation is unaffected.
- The history shows what was actually cooked, not the recipe's current version.

Same criterion as personalizations (a fork) and discovery sessions (a pantry
snapshot): what the user is doing belongs to the user's own model.

Rules:
- Only one preparation in progress per user and recipe (enforced by the use
  case, backed by a partial unique index).
- Steps can be completed in any order; completing the current step moves to
  the next pending one. Any step can be visited.
- A step timer can be (re)started only on a step that has a timer.
- Once completed or abandoned, a preparation is read-only history.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from app.preparation.domain.exceptions import (
    PreparationNotInProgressError,
    PreparationStepNotFoundError,
    StepHasNoTimerError,
)
from app.preparation.domain.services.ports import RecipeToPrepare
from app.preparation.domain.value_objects.preparation_session_id import PreparationSessionId


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PreparationStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass(frozen=True)
class PreparedIngredient:
    """Copy of an ingredient line, in the recipe's original units (conversion is display-only)."""

    ingredient_id: str
    ingredient_name: str | None
    quantity: Decimal
    unit_id: str
    unit_abbreviation: str | None
    notes: str | None
    position: int


@dataclass
class PreparedStep:
    step_number: int
    instructions: str
    title: str | None = None
    timer_seconds: int | None = None
    photo_url: str | None = None
    source_step_id: str | None = None
    completed_at: datetime | None = None
    timer_started_at: datetime | None = None

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    def timer_remaining_seconds(self, now: datetime) -> int | None:
        """Seconds left on a running timer (0 when it has rung); None if it was never started."""
        if self.timer_seconds is None or self.timer_started_at is None:
            return None
        elapsed = (now - self.timer_started_at).total_seconds()
        return max(0, int(self.timer_seconds - elapsed))


@dataclass
class PreparationSession:
    id: PreparationSessionId
    user_id: str
    recipe_id: str
    recipe_title: str
    cover_photo_url: str | None
    servings: int | None
    status: PreparationStatus
    current_step_number: int | None
    ingredients: list[PreparedIngredient] = field(default_factory=list)
    steps: list[PreparedStep] = field(default_factory=list)
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None

    @classmethod
    def start(cls, user_id: str, recipe: RecipeToPrepare) -> "PreparationSession":
        steps = [
            PreparedStep(
                step_number=step.step_number,
                instructions=step.instructions,
                title=step.title,
                timer_seconds=step.timer_seconds,
                photo_url=step.photo_url,
                source_step_id=step.source_step_id,
            )
            for step in sorted(recipe.steps, key=lambda step: step.step_number)
        ]
        return cls(
            id=PreparationSessionId(),
            user_id=user_id,
            recipe_id=recipe.id,
            recipe_title=recipe.title,
            cover_photo_url=recipe.cover_photo_url,
            servings=recipe.servings,
            status=PreparationStatus.IN_PROGRESS,
            current_step_number=steps[0].step_number if steps else None,
            ingredients=[
                PreparedIngredient(
                    ingredient_id=line.ingredient_id,
                    ingredient_name=line.ingredient_name,
                    quantity=line.quantity,
                    unit_id=line.unit_id,
                    unit_abbreviation=line.unit_abbreviation,
                    notes=line.notes,
                    position=line.position,
                )
                for line in sorted(recipe.ingredients, key=lambda line: line.position)
            ],
            steps=steps,
        )

    # --- Queries ---------------------------------------------------------------

    def is_owned_by(self, user_id: str) -> bool:
        return self.user_id == user_id

    @property
    def is_in_progress(self) -> bool:
        return self.status == PreparationStatus.IN_PROGRESS

    @property
    def completed_steps(self) -> int:
        return sum(1 for step in self.steps if step.is_completed)

    # --- Commands --------------------------------------------------------------

    def go_to_step(self, step_number: int) -> None:
        self._ensure_in_progress()
        self.current_step_number = self._step(step_number).step_number

    def complete_step(self, step_number: int, now: datetime) -> None:
        self._ensure_in_progress()
        step = self._step(step_number)
        if not step.is_completed:
            step.completed_at = now
        if self.current_step_number == step_number:
            self.current_step_number = self._next_pending_after(step_number)

    def uncomplete_step(self, step_number: int) -> None:
        self._ensure_in_progress()
        self._step(step_number).completed_at = None

    def start_timer(self, step_number: int, now: datetime) -> None:
        self._ensure_in_progress()
        step = self._step(step_number)
        if step.timer_seconds is None:
            raise StepHasNoTimerError(step_number)
        step.timer_started_at = now  # starting again restarts it

    def finish(self, now: datetime) -> None:
        """Done cooking. Pending steps stay pending: the history shows how much was followed."""
        self._ensure_in_progress()
        self.status = PreparationStatus.COMPLETED
        self.finished_at = now

    def abandon(self, now: datetime) -> None:
        self._ensure_in_progress()
        self.status = PreparationStatus.ABANDONED
        self.finished_at = now

    # --- Internals ---------------------------------------------------------------

    def _ensure_in_progress(self) -> None:
        if not self.is_in_progress:
            raise PreparationNotInProgressError(self.status.value.replace("_", " "))

    def _step(self, step_number: int) -> PreparedStep:
        step = next((step for step in self.steps if step.step_number == step_number), None)
        if step is None:
            raise PreparationStepNotFoundError(step_number)
        return step

    def _next_pending_after(self, step_number: int) -> int:
        """Next pending step after `step_number`, wrapping around; stays put if everything is done."""
        ordered = [step.step_number for step in self.steps]
        index = ordered.index(step_number)
        for candidate in ordered[index + 1 :] + ordered[: index + 1]:
            if not self._step(candidate).is_completed:
                return candidate
        return step_number
