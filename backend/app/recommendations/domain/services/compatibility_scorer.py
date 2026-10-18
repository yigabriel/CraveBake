"""
CompatibilityScorer — how well a recipe fits what the user has.

This is where the recommendation rule lives:

- `ingredient_score` = share of the recipe's ingredients the user has
  (presence only: quantities are not compared, the temporary selection has
  none and pantry quantities are optional).
- `equipment_score` = share of the recipe's equipment the user owns
  (1.0 when the recipe lists no equipment: nothing is missing).
- `rank_score` = weighted blend used to order the deck. Ingredients weigh
  most; equipment *prioritizes but never excludes*: a recipe needing a mold
  you don't own still shows up, just lower than an equally compatible one
  you can make with your kitchen.

The deck is ranked by the database for performance, but with *these*
weights (passed along by the use case), and every card shown is scored
here, so the rule has a single owner.
"""
from __future__ import annotations

from dataclasses import dataclass

INGREDIENT_WEIGHT = 0.8
EQUIPMENT_WEIGHT = 0.2


@dataclass(frozen=True)
class Compatibility:
    ingredient_score: float
    equipment_score: float
    rank_score: float
    matched_ingredient_ids: frozenset[str]
    missing_ingredient_ids: frozenset[str]
    missing_equipment_ids: frozenset[str]

    @property
    def has_all_equipment(self) -> bool:
        return not self.missing_equipment_ids


class CompatibilityScorer:
    def __init__(self, ingredient_weight: float = INGREDIENT_WEIGHT, equipment_weight: float = EQUIPMENT_WEIGHT) -> None:
        self.ingredient_weight = ingredient_weight
        self.equipment_weight = equipment_weight

    def score(
        self,
        recipe_ingredient_ids: frozenset[str],
        recipe_equipment_ids: frozenset[str],
        available_ingredient_ids: set[str],
        available_equipment_ids: set[str],
    ) -> Compatibility:
        matched = recipe_ingredient_ids & available_ingredient_ids
        missing_equipment = recipe_equipment_ids - available_equipment_ids

        ingredient_score = len(matched) / len(recipe_ingredient_ids) if recipe_ingredient_ids else 0.0
        equipment_score = (
            1 - len(missing_equipment) / len(recipe_equipment_ids) if recipe_equipment_ids else 1.0
        )
        rank_score = self.ingredient_weight * ingredient_score + self.equipment_weight * equipment_score

        return Compatibility(
            ingredient_score=round(ingredient_score, 4),
            equipment_score=round(equipment_score, 4),
            rank_score=round(rank_score, 4),
            matched_ingredient_ids=frozenset(matched),
            missing_ingredient_ids=frozenset(recipe_ingredient_ids - matched),
            missing_equipment_ids=frozenset(missing_equipment),
        )
