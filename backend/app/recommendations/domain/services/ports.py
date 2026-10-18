"""
Ports towards the bounded contexts recommendations reads from or writes to.

Defined from this module's point of view (what *recommendations* needs),
not mirroring the upstream APIs. Each one is implemented by an
anti-corruption-layer adapter in infrastructure.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CandidateRecipe:
    """A recipe as recommendations sees it: a card plus what it is made with."""

    id: str
    title: str
    description: str | None
    cover_photo_url: str | None
    category_name: str | None
    difficulty_name: str | None
    prep_time_minutes: int | None
    servings: int | None
    created_by_user_id: str
    is_personalization: bool
    source_recipe_title: str | None
    tag_names: tuple[str, ...]
    ingredient_ids: frozenset[str]
    equipment_ids: frozenset[str]


@dataclass(frozen=True)
class CandidateRankingRequest:
    """Which recipes to rank for a deck page, and how to weigh them.

    The weights come from this module's `CompatibilityScorer`: the ranking
    rule is ours, the recipes context only executes it efficiently.
    """

    viewer_user_id: str
    ingredient_ids: list[str]
    equipment_ids: list[str]
    ingredient_weight: float
    equipment_weight: float
    min_ingredient_score: float
    excluded_recipe_ids: list[str] = field(default_factory=list)
    category_id: str | None = None
    tag_ids: list[str] = field(default_factory=list)
    limit: int = 10
    offset: int = 0


@dataclass(frozen=True)
class CandidateRankingPage:
    recipe_ids: list[str]  # best first
    total: int


class RecipeCandidateSource(ABC):
    """Recipes context."""

    @abstractmethod
    async def rank(self, request: CandidateRankingRequest) -> CandidateRankingPage:
        """Recipes the viewer can see (public or their own; their personalization replaces the
        original) that use at least one of the ingredients, best first."""

    @abstractmethod
    async def get_many_visible(self, recipe_ids: list[str], viewer_user_id: str) -> list[CandidateRecipe]:
        """In the given order; recipes the viewer may not see are left out."""

    @abstractmethod
    async def get_visible(self, recipe_id: str, viewer_user_id: str) -> CandidateRecipe | None:
        ...

    @abstractmethod
    async def category_names(self) -> dict[str, str]:
        """Every recipe category, id -> name."""

    @abstractmethod
    async def tag_names(self) -> dict[str, str]:
        """Every recipe tag, id -> name."""


class KitchenCatalog(ABC):
    """Ingredients + equipment contexts: what the user has, and display names."""

    @abstractmethod
    async def pantry_ingredient_ids(self, user_id: str) -> list[str]:
        ...

    @abstractmethod
    async def user_equipment_ids(self, user_id: str) -> list[str]:
        ...

    @abstractmethod
    async def ingredient_names(self, ids: list[str]) -> dict[str, str]:
        """Existing ingredients keyed by id; unknown ids are omitted."""

    @abstractmethod
    async def equipment_names(self, ids: list[str]) -> dict[str, str]:
        """Existing equipment keyed by id; unknown ids are omitted."""


class FavoritesGateway(ABC):
    """Portfolio context."""

    @abstractmethod
    async def save(self, user_id: str, recipe_id: str) -> None:
        ...

    @abstractmethod
    async def saved_among(self, user_id: str, recipe_ids: list[str]) -> set[str]:
        ...
