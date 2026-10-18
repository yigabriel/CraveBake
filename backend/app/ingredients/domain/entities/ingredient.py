"""
Ingredient entity — a reusable catalog item.

An Ingredient belongs to the general database, not to any single user: the
same "Harina" row is referenced by every recipe and every pantry that uses
flour. Uniqueness of `name` is a domain invariant enforced by the use case
(via the repository) before this entity is even constructed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.shared.exceptions.domain_exceptions import ValidationError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Ingredient:
    id: IngredientId
    name: str
    description: str | None = None
    default_category: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @classmethod
    def create(
        cls,
        name: str,
        description: str | None = None,
        default_category: str | None = None,
    ) -> "Ingredient":
        return cls(id=IngredientId(), name=_clean_name(name), description=description, default_category=default_category)

    def rename(self, new_name: str) -> None:
        self.name = _clean_name(new_name)


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValidationError("Ingredient name cannot be empty")
    return cleaned
