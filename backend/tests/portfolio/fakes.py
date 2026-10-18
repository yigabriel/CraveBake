"""In-memory test doubles for the portfolio ports."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from app.portfolio.domain.entities.saved_recipe import SavedRecipe
from app.portfolio.domain.repositories.saved_recipe_repository import SavedRecipeRepository
from app.portfolio.domain.services.recipe_catalog import RecipeCatalog, RecipeSnapshot

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_snapshot(
    title: str = "Brownies",
    owner: str = "author",
    is_public: bool = True,
    source_recipe_id: str | None = None,
    category_id: str | None = None,
    tag_ids: frozenset[str] = frozenset(),
    created_minutes: int = 0,
) -> RecipeSnapshot:
    created_at = BASE_TIME + timedelta(minutes=created_minutes)
    return RecipeSnapshot(
        id=str(uuid.uuid4()),
        title=title,
        description=None,
        cover_photo_url=None,
        category_id=category_id,
        category_name=None,
        tag_ids=tag_ids,
        tag_names=tuple(sorted(tag_ids)),
        difficulty_name=None,
        prep_time_minutes=None,
        servings=None,
        is_public=is_public,
        created_by_user_id=owner,
        source_recipe_id=source_recipe_id,
        source_recipe_title=None,
        source_updated_since_personalized=None,
        created_at=created_at,
        updated_at=created_at,
    )


class FakeRecipeCatalog(RecipeCatalog):
    """Visibility rule mirrored from recipes: public, or owned by the viewer."""

    def __init__(self, *recipes: RecipeSnapshot) -> None:
        self.recipes = {recipe.id: recipe for recipe in recipes}

    def add(self, recipe: RecipeSnapshot) -> RecipeSnapshot:
        self.recipes[recipe.id] = recipe
        return recipe

    def _visible(self, recipe: RecipeSnapshot | None, viewer: str) -> bool:
        return recipe is not None and (recipe.is_public or recipe.created_by_user_id == viewer)

    async def get_visible(self, recipe_id, viewer_user_id):
        recipe = self.recipes.get(recipe_id)
        return recipe if self._visible(recipe, viewer_user_id) else None

    async def get_many_visible(self, recipe_ids, viewer_user_id):
        return {
            rid: self.recipes[rid]
            for rid in recipe_ids
            if self._visible(self.recipes.get(rid), viewer_user_id)
        }

    async def list_owned_by(self, user_id):
        return [r for r in self.recipes.values() if r.created_by_user_id == user_id]


class InMemorySavedRecipeRepository(SavedRecipeRepository):

    def __init__(self) -> None:
        self.items: list[SavedRecipe] = []

    async def add(self, saved_recipe: SavedRecipe) -> None:
        self.items.append(saved_recipe)

    async def remove(self, user_id: str, recipe_id: str) -> None:
        self.items = [s for s in self.items if not (s.user_id == user_id and s.recipe_id == recipe_id)]

    async def get(self, user_id: str, recipe_id: str) -> SavedRecipe | None:
        return next((s for s in self.items if s.user_id == user_id and s.recipe_id == recipe_id), None)

    async def list_by_user(self, user_id: str) -> list[SavedRecipe]:
        return [s for s in self.items if s.user_id == user_id]

    async def list_by_user_and_recipes(self, user_id: str, recipe_ids: list[str]) -> list[SavedRecipe]:
        return [s for s in self.items if s.user_id == user_id and s.recipe_id in recipe_ids]
