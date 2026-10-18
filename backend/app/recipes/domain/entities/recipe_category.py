"""
RecipeCategory — controlled catalog of recipe categories (tortas, galletas, ...).

Not to be confused with the ingredients' `default_category`, which is free
text: recipe categories are a curated list seeded by migration.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.recipes.domain.value_objects.recipe_category_id import RecipeCategoryId


@dataclass
class RecipeCategory:
    id: RecipeCategoryId
    name: str
