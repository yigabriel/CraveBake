"""
PreparationAssembler — turns a PreparationSession into DTOs.

Quantities are shown in the requested unit system through the ingredients
context (`QuantityDisplay` port); 'original' shows them as the recipe was
written. The stored copy is never modified.
"""
from __future__ import annotations

from datetime import datetime

from app.preparation.application.dto.preparation_dto import (
    PreparationDetailDTO,
    PreparationSummaryDTO,
    PreparedIngredientDTO,
    PreparedStepDTO,
)
from app.preparation.domain.entities.preparation_session import PreparationSession
from app.preparation.domain.services.ports import QuantityDisplay, QuantityToShow, ShownQuantity

ORIGINAL_UNITS = "original"


def to_summary(session: PreparationSession) -> PreparationSummaryDTO:
    return PreparationSummaryDTO(
        id=str(session.id),
        recipe_id=session.recipe_id,
        recipe_title=session.recipe_title,
        cover_photo_url=session.cover_photo_url,
        status=session.status.value,
        completed_steps=session.completed_steps,
        total_steps=len(session.steps),
        started_at=session.started_at,
        finished_at=session.finished_at,
    )


class PreparationAssembler:
    def __init__(self, quantity_display: QuantityDisplay) -> None:
        self._quantity_display = quantity_display

    async def to_detail(self, session: PreparationSession, unit_system: str, now: datetime) -> PreparationDetailDTO:
        if unit_system == ORIGINAL_UNITS:
            shown = [
                ShownQuantity(line.quantity, line.unit_abbreviation or "", converted=False)
                for line in session.ingredients
            ]
        else:
            shown = await self._quantity_display.show_in(
                [QuantityToShow(line.ingredient_id, line.quantity, line.unit_id) for line in session.ingredients],
                unit_system,
            )

        return PreparationDetailDTO(
            id=str(session.id),
            recipe_id=session.recipe_id,
            recipe_title=session.recipe_title,
            cover_photo_url=session.cover_photo_url,
            servings=session.servings,
            status=session.status.value,
            unit_system=unit_system,
            current_step_number=session.current_step_number,
            completed_steps=session.completed_steps,
            total_steps=len(session.steps),
            ingredients=[
                PreparedIngredientDTO(
                    ingredient_id=line.ingredient_id,
                    ingredient_name=line.ingredient_name,
                    quantity=display.quantity,
                    unit_abbreviation=display.unit_abbreviation or line.unit_abbreviation,
                    original_quantity=line.quantity,
                    original_unit_abbreviation=line.unit_abbreviation,
                    converted=display.converted,
                    notes=line.notes,
                )
                for line, display in zip(session.ingredients, shown)
            ],
            steps=[
                PreparedStepDTO(
                    step_number=step.step_number,
                    title=step.title,
                    instructions=step.instructions,
                    photo_url=step.photo_url,
                    timer_seconds=step.timer_seconds,
                    timer_started_at=step.timer_started_at,
                    timer_remaining_seconds=step.timer_remaining_seconds(now),
                    is_completed=step.is_completed,
                    completed_at=step.completed_at,
                    is_current=step.step_number == session.current_step_number,
                )
                for step in session.steps
            ],
            started_at=session.started_at,
            finished_at=session.finished_at,
        )
