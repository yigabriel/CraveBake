"""
Ports of the recipe import: where the text comes from, who reads it, and the catalog it is matched to.

Each one is an external or cross-module dependency, so each can be swapped (another transcript
provider, another model) by writing one adapter, without touching the use case.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.recipe_import.domain.extracted_recipe import ExtractedRecipe
from app.recipe_import.domain.source_url import SourceUrl
from app.recipe_import.domain.video_text import VideoText
from app.shared.domain.value_objects.localized_text import LocalizedText


class VideoTextSource(ABC):
    @abstractmethod
    async def fetch(self, source: SourceUrl) -> VideoText:
        """Title, description and the platform's own captions of the video.

        Raises `VideoUnavailableError` for a private/removed video and `ImportUnavailableError`
        when the provider cannot be used (no key, no credits, down).
        """


@dataclass(frozen=True)
class CatalogIngredient:
    id: str
    name: LocalizedText


@dataclass(frozen=True)
class CatalogEquipment:
    id: str
    name: LocalizedText


@dataclass(frozen=True)
class CatalogCategory:
    id: str
    name: LocalizedText


@dataclass(frozen=True)
class CatalogDifficulty:
    id: str
    name: LocalizedText
    level_order: int


@dataclass(frozen=True)
class ExtractionCatalog:
    """The names the model may choose from, as plain text (in the catalog's own order)."""

    ingredients: list[str]
    units: list[str]
    equipment: list[str]
    categories: list[str]


@dataclass(frozen=True)
class CatalogUnit:
    id: str
    name: LocalizedText
    abbreviation: str


class ImportCatalog(ABC):
    """The ingredients module, seen from here (anti-corruption layer)."""

    @abstractmethod
    async def ingredients(self) -> list[CatalogIngredient]: ...

    @abstractmethod
    async def units(self) -> list[CatalogUnit]: ...

    @abstractmethod
    async def equipment(self) -> list[CatalogEquipment]: ...

    @abstractmethod
    async def categories(self) -> list[CatalogCategory]: ...

    @abstractmethod
    async def difficulties(self) -> list[CatalogDifficulty]: ...


class RecipeExtractor(ABC):
    @abstractmethod
    async def extract(self, text: VideoText, catalog: ExtractionCatalog) -> ExtractedRecipe:
        """Reads the text. `catalog` holds the names it may choose from."""
