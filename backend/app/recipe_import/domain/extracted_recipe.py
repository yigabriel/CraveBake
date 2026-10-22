"""
What the model understood from the text: a recipe as written, before anything is checked against the catalog.

Everything here is a claim to be verified by the person importing it. Quantities may be
missing (a caption that says "a splash of milk"), units are the catalog's abbreviations
or nothing, and `catalog_name` is the model's pick from the ingredient list it was given.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

MAX_INGREDIENTS = 80
MAX_STEPS = 60
MAX_EQUIPMENT = 30


@dataclass(frozen=True)
class ExtractedIngredient:
    name: str  # as the video says it
    catalog_name: str | None = None  # the catalog entry the model matched it to, if any
    quantity: Decimal | None = None
    unit: str | None = None  # a catalog unit abbreviation
    notes: str | None = None
    section: str | None = None  # "Dough", "Filling"...


@dataclass(frozen=True)
class ExtractedStep:
    instructions: str
    title: str | None = None
    timer_minutes: Decimal | None = None
    section: str | None = None


@dataclass(frozen=True)
class ExtractedRecipe:
    is_recipe: bool
    title: str = ""
    description: str | None = None
    servings: int | None = None
    prep_time_minutes: int | None = None
    ingredients: list[ExtractedIngredient] = field(default_factory=list)
    steps: list[ExtractedStep] = field(default_factory=list)
    equipment: list[str] = field(default_factory=list)  # names from the equipment catalog
    category: str | None = None  # a name from the recipe-category catalog
