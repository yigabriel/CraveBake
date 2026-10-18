"""DTOs for the ingredients catalog."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateIngredientDTO:
    name: str
    description: str | None = None
    default_category: str | None = None


@dataclass(frozen=True)
class SearchIngredientsDTO:
    query: str | None = None
    category: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class IngredientDTO:
    id: str
    name: str
    description: str | None
    default_category: str | None
