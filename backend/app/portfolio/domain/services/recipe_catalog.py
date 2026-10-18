"""
RecipeCatalog — port towards the recipes bounded context.

Portfolio never imports recipes' domain: it sees a recipe as a read-only
`RecipeSnapshot`, with just what "Mi Portafolio" needs to render a card.

Visibility (deleted, private, ...) is the recipes context's rule, not ours:
the catalog only ever returns recipes the viewer is allowed to see, so this
module never re-implements that rule.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RecipeSnapshot:
    id: str
    title: str
    description: str | None
    cover_photo_url: str | None
    category_id: str | None
    category_name: str | None
    tag_ids: frozenset[str]
    tag_names: tuple[str, ...]
    difficulty_name: str | None
    prep_time_minutes: int | None
    servings: int | None
    is_public: bool
    created_by_user_id: str
    source_recipe_id: str | None
    source_recipe_title: str | None
    source_updated_since_personalized: bool | None
    created_at: datetime
    updated_at: datetime

    @property
    def is_personalization(self) -> bool:
        return self.source_recipe_id is not None

    def is_owned_by(self, user_id: str) -> bool:
        return self.created_by_user_id == user_id

    def matches(self, category_id: str | None, tag_ids: list[str]) -> bool:
        """True if the recipe is in `category_id` (when given) and has every tag in `tag_ids`."""
        if category_id is not None and self.category_id != category_id:
            return False
        return self.tag_ids.issuperset(tag_ids)


class RecipeCatalog(ABC):
    @abstractmethod
    async def get_visible(self, recipe_id: str, viewer_user_id: str) -> RecipeSnapshot | None:
        """None if the recipe does not exist or the viewer may not see it."""

    @abstractmethod
    async def get_many_visible(self, recipe_ids: list[str], viewer_user_id: str) -> dict[str, RecipeSnapshot]:
        """Keyed by recipe id; recipes that don't exist or aren't visible are omitted."""

    @abstractmethod
    async def list_owned_by(self, user_id: str) -> list[RecipeSnapshot]:
        """Non-deleted recipes created by the user (originals and personalizations)."""
