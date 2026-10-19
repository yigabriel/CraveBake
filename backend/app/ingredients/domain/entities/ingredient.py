"""
Ingredient entity — a reusable catalog item.

An Ingredient belongs to the general database, not to any single user: the
same "Harina" row is referenced by every recipe and every pantry that uses
flour. Its name is a LocalizedText: written in one language by whoever created
it, possibly translated to others. A name must not clash with any existing
ingredient's name in any language — a domain invariant enforced by the use
case (via the repository) before this entity is even constructed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.shared.domain.value_objects.localized_text import DEFAULT_LANGUAGE, LocalizedText


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Ingredient:
    id: IngredientId
    name: LocalizedText
    description: str | None = None
    default_category: str | None = None  # stable code, e.g. "harina"
    # Display name of `default_category` (read-only, resolved by the repository).
    category_name: LocalizedText | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @classmethod
    def create(
        cls,
        name: str,
        language: str = DEFAULT_LANGUAGE,
        description: str | None = None,
        default_category: str | None = None,
    ) -> "Ingredient":
        """`language`: the language `name` is written in (the creator's)."""
        return cls(
            id=IngredientId(),
            name=LocalizedText.of(name, language),
            description=description,
            default_category=default_category,
        )

    def translate(self, language: str, text: str) -> None:
        self.name = self.name.with_translation(language, text)
