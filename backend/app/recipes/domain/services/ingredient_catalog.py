"""
IngredientCatalog — port towards the ingredients bounded context.

Recipes reference ingredients and units by opaque ids. This port is how the
recipes module checks those ids exist and fetches their display names,
without importing anything from the ingredients module's domain.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.value_objects.localized_text import LocalizedText


@dataclass(frozen=True)
class CatalogIngredient:
    id: str
    name: LocalizedText


@dataclass(frozen=True)
class CatalogUnit:
    id: str
    name: str
    abbreviation: str


@dataclass(frozen=True)
class QuantityToDisplay:
    ingredient_id: str
    quantity: Decimal
    unit_id: str


@dataclass(frozen=True)
class DisplayedQuantity:
    quantity: Decimal
    unit_abbreviation: str
    converted: bool


class IngredientCatalog(ABC):
    @abstractmethod
    async def get_ingredients(self, ids: list[str]) -> dict[str, CatalogIngredient]:
        """Returns the ingredients that exist, keyed by id. Unknown ids are omitted."""

    @abstractmethod
    async def get_units(self, ids: list[str]) -> dict[str, CatalogUnit]:
        """Returns the units that exist, keyed by id. Unknown ids are omitted."""

    @abstractmethod
    async def display_in(self, quantities: list[QuantityToDisplay], unit_system: str) -> list[DisplayedQuantity]:
        """Each quantity expressed in `unit_system` ('metric' | 'us'), same order (display only)."""
