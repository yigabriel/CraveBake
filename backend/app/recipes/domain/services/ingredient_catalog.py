"""
IngredientCatalog — port towards the ingredients bounded context.

Recipes reference ingredients and units by opaque ids. This port is how the
recipes module checks those ids exist and fetches their display names,
without importing anything from the ingredients module's domain.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogIngredient:
    id: str
    name: str


@dataclass(frozen=True)
class CatalogUnit:
    id: str
    name: str
    abbreviation: str


class IngredientCatalog(ABC):
    @abstractmethod
    async def get_ingredients(self, ids: list[str]) -> dict[str, CatalogIngredient]:
        """Returns the ingredients that exist, keyed by id. Unknown ids are omitted."""

    @abstractmethod
    async def get_units(self, ids: list[str]) -> dict[str, CatalogUnit]:
        """Returns the units that exist, keyed by id. Unknown ids are omitted."""
