"""
RecipeIngredient — one ingredient line of a recipe (e.g. "250 g de harina").

`ingredient_id` and `unit_id` are opaque strings minted by the ingredients
bounded context: recipes never import ingredients' domain types. The stored
quantity is the real value of the recipe; the user's `preferred_unit_system`
only changes how it is displayed, never this data.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.recipes.domain.value_objects.recipe_ingredient_id import RecipeIngredientId
from app.shared.exceptions.domain_exceptions import ValidationError


@dataclass
class RecipeIngredient:
    id: RecipeIngredientId
    ingredient_id: str
    quantity: Decimal
    unit_id: str
    notes: str | None = None
    position: int = 0

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValidationError("Ingredient quantity must be greater than zero")
        if self.notes is not None:
            self.notes = self.notes.strip() or None
