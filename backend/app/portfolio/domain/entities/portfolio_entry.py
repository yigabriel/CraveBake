"""
PortfolioEntry — one card of "Mi Portafolio".

The portfolio is not stored anywhere: it is derived from the user's own
recipes (originals and personalizations, owned by the recipes context) plus
their saved recipes (owned by this context). `build_portfolio` is the one
place that decides what shows up and under which kind.

The kinds use the same words as the recipes context ('original',
'personalized') plus 'saved', so the whole API speaks one language.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.portfolio.domain.entities.saved_recipe import SavedRecipe
from app.portfolio.domain.services.recipe_catalog import RecipeSnapshot


class PortfolioItemKind(str, Enum):
    ORIGINAL = "original"  # recipes the user wrote from scratch
    PERSONALIZED = "personalized"  # the user's private variants of other recipes
    SAVED = "saved"  # favorites: public recipes of other users


@dataclass(frozen=True)
class PortfolioEntry:
    kind: PortfolioItemKind
    recipe: RecipeSnapshot
    added_at: datetime  # created_at for original/personalized, saved_at for favorites


def build_portfolio(
    user_id: str,
    owned_recipes: list[RecipeSnapshot],
    saved_recipes: list[SavedRecipe],
    visible_saved_recipes: dict[str, RecipeSnapshot],
) -> list[PortfolioEntry]:
    """Merges owned and saved recipes, newest first.

    Saved recipes missing from `visible_saved_recipes` (deleted, or made
    private by their author) are left out.
    """
    entries = [
        PortfolioEntry(
            kind=PortfolioItemKind.PERSONALIZED if recipe.is_personalization else PortfolioItemKind.ORIGINAL,
            recipe=recipe,
            added_at=recipe.created_at,
        )
        for recipe in owned_recipes
    ]
    for saved in saved_recipes:
        snapshot = visible_saved_recipes.get(saved.recipe_id)
        if snapshot is None or snapshot.is_owned_by(user_id):
            continue
        entries.append(PortfolioEntry(kind=PortfolioItemKind.SAVED, recipe=snapshot, added_at=saved.saved_at))

    entries.sort(key=lambda entry: entry.added_at, reverse=True)
    return entries
