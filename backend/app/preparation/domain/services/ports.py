"""
Ports towards the bounded contexts preparation reads from.

Defined from this module's point of view; implemented by anti-corruption
layer adapters in infrastructure.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.value_objects.localized_text import LocalizedText


@dataclass(frozen=True)
class IngredientToPrepare:
    ingredient_id: str
    ingredient_name: LocalizedText | None
    quantity: Decimal
    unit_id: str
    unit_abbreviation: str | None
    notes: str | None
    position: int
    section: str | None = None  # name of the recipe's group it belongs to


@dataclass(frozen=True)
class StepToPrepare:
    source_step_id: str
    step_number: int
    instructions: str
    title: str | None
    timer_seconds: int | None
    photo_url: str | None
    section: str | None = None  # name of the recipe's group it belongs to


@dataclass(frozen=True)
class RecipeToPrepare:
    """Everything needed to cook a recipe, as it is right now (it will be copied)."""

    id: str
    title: str
    cover_photo_url: str | None
    servings: int | None
    ingredients: list[IngredientToPrepare]
    steps: list[StepToPrepare]


@dataclass(frozen=True)
class QuantityToShow:
    ingredient_id: str
    quantity: Decimal
    unit_id: str


@dataclass(frozen=True)
class ShownQuantity:
    quantity: Decimal
    unit_abbreviation: str
    converted: bool


class RecipeSource(ABC):
    """Recipes context."""

    @abstractmethod
    async def get_recipe_to_prepare(self, recipe_id: str, viewer_user_id: str) -> RecipeToPrepare | None:
        """None if the recipe does not exist or the viewer may not see it."""


class QuantityDisplay(ABC):
    """Ingredients context: shows quantities in the user's unit system (display only)."""

    @abstractmethod
    async def show_in(self, quantities: list[QuantityToShow], unit_system: str) -> list[ShownQuantity]:
        """Same order as given; `unit_system` is 'metric' or 'us'."""
