"""
DiscoverySession — aggregate root of "¿Qué quiero cocinar?" (Tinder style).

A session freezes what the user wants to cook: the ingredients (either a
temporary selection, never stored in the pantry, or a snapshot of the
pantry taken when the session starts) and optional filters (one recipe
category, any number of tags). The deck stays stable while the user swipes
even if the pantry changes meanwhile.

Swipes are remembered *only inside the session*: a recipe swiped here does
not come back in this session's deck, but a new session starts clean. Each
recipe can be swiped once per session.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.recommendations.domain.exceptions import NoIngredientsAvailableError, RecipeAlreadySwipedError
from app.recommendations.domain.value_objects.discovery_session_id import DiscoverySessionId
from app.recommendations.domain.value_objects.swipe_id import SwipeId
from app.shared.exceptions.domain_exceptions import ValidationError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IngredientSource(str, Enum):
    SELECTION = "selection"  # chosen for this search only
    PANTRY = "pantry"  # snapshot of the user's pantry


class SwipeAction(str, Enum):
    DISCARDED = "discarded"
    SAVED = "saved"  # also added to the user's favorites
    SELECTED = "selected"  # "I want to cook this one"


@dataclass(frozen=True)
class Swipe:
    id: SwipeId
    recipe_id: str
    action: SwipeAction
    compatibility_score: float
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class DiscoverySession:
    id: DiscoverySessionId
    user_id: str
    ingredient_source: IngredientSource
    ingredient_ids: list[str]
    min_score: float = 0.0
    category_id: str | None = None  # opaque id of a recipes-context category
    tag_ids: list[str] = field(default_factory=list)  # opaque ids of recipes-context tags (recipe must have all)
    swipes: list[Swipe] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)

    @classmethod
    def start(
        cls,
        user_id: str,
        selected_ingredient_ids: list[str],
        pantry_ingredient_ids: list[str],
        min_score: float = 0.0,
        category_id: str | None = None,
        tag_ids: list[str] | None = None,
    ) -> "DiscoverySession":
        if not 0 <= min_score <= 1:
            raise ValidationError("min_score must be between 0 and 1")
        if selected_ingredient_ids:
            source, ingredient_ids = IngredientSource.SELECTION, selected_ingredient_ids
        elif pantry_ingredient_ids:
            source, ingredient_ids = IngredientSource.PANTRY, pantry_ingredient_ids
        else:
            raise NoIngredientsAvailableError()
        return cls(
            id=DiscoverySessionId(),
            user_id=user_id,
            ingredient_source=source,
            ingredient_ids=list(dict.fromkeys(ingredient_ids)),  # de-duplicated, order preserved
            min_score=min_score,
            category_id=category_id,
            tag_ids=list(dict.fromkeys(tag_ids or [])),
        )

    def is_owned_by(self, user_id: str) -> bool:
        return self.user_id == user_id

    @property
    def swiped_recipe_ids(self) -> set[str]:
        return {swipe.recipe_id for swipe in self.swipes}

    def swipe_counts(self) -> dict[SwipeAction, int]:
        counts = Counter(swipe.action for swipe in self.swipes)
        return {action: counts[action] for action in SwipeAction}

    def swipe(self, recipe_id: str, action: SwipeAction, compatibility_score: float) -> Swipe:
        if recipe_id in self.swiped_recipe_ids:
            raise RecipeAlreadySwipedError(recipe_id)
        swipe = Swipe(id=SwipeId(), recipe_id=recipe_id, action=action, compatibility_score=compatibility_score)
        self.swipes.append(swipe)
        return swipe
