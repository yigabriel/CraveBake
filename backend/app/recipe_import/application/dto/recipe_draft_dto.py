"""DTOs of the recipe import: the draft handed back to be reviewed (nothing is saved)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.shared.domain.value_objects.localized_text import LocalizedText


@dataclass(frozen=True)
class ImportRecipeDTO:
    url: str
    user_id: str = ""  # who imports: the cover copy goes to their folder


@dataclass(frozen=True)
class DraftCatalogItemDTO:
    id: str
    name: LocalizedText
    abbreviation: str | None = None  # units only


@dataclass(frozen=True)
class DraftIngredientDTO:
    raw_name: str  # as the video says it
    ingredient: DraftCatalogItemDTO | None  # None: not in the catalog, the person must pick or create it
    quantity: Decimal | None
    unit: DraftCatalogItemDTO | None
    notes: str | None
    section: str | None


@dataclass(frozen=True)
class DraftStepDTO:
    instructions: str
    title: str | None
    timer_minutes: Decimal | None
    section: str | None


@dataclass(frozen=True)
class WhatWasReadDTO:
    title: bool
    description: bool
    transcript: bool


@dataclass(frozen=True)
class RecipeDraftDTO:
    title: str
    description: str | None
    servings: int | None
    prep_time_minutes: int | None
    source_url: str
    platform: str
    author: str | None
    read: WhatWasReadDTO
    ingredients: list[DraftIngredientDTO] = field(default_factory=list)
    steps: list[DraftStepDTO] = field(default_factory=list)
    equipment: list[DraftCatalogItemDTO] = field(default_factory=list)  # only catalog items: a recipe can only list those
    category: DraftCatalogItemDTO | None = None
    difficulty: DraftCatalogItemDTO | None = None  # always the middle level: a caption cannot say how hard a recipe is
    cover_url: str | None = None  # our copy of the video's cover frame, to add as the first cover once saved
