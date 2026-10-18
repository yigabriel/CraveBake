"""
SavedRecipe — a favorite: a public recipe of someone else that the user saved.

Only recipes the user can see can be saved (the `RecipeCatalog` only hands
out visible ones), and never the user's own recipes, which are already part
of their portfolio. If the recipe is later deleted or made private, the row
stays, but the recipe stops showing up in the portfolio.

`user_id` and `recipe_id` are opaque ids from IAM and recipes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.portfolio.domain.exceptions import CannotSaveOwnRecipeError
from app.portfolio.domain.services.recipe_catalog import RecipeSnapshot
from app.portfolio.domain.value_objects.saved_recipe_id import SavedRecipeId


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SavedRecipe:
    id: SavedRecipeId
    user_id: str
    recipe_id: str
    saved_at: datetime = field(default_factory=_utc_now)

    @classmethod
    def save(cls, user_id: str, visible_recipe: RecipeSnapshot) -> "SavedRecipe":
        if visible_recipe.is_owned_by(user_id):
            raise CannotSaveOwnRecipeError()
        return cls(id=SavedRecipeId(), user_id=user_id, recipe_id=visible_recipe.id)
