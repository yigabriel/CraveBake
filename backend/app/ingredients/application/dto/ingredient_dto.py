"""DTOs for the ingredients catalog."""
from dataclasses import dataclass

from app.shared.domain.value_objects.localized_text import DEFAULT_LANGUAGE, LocalizedText


@dataclass(frozen=True)
class CreateIngredientDTO:
    name: str
    description: str | None = None
    default_category: str | None = None
    language: str = DEFAULT_LANGUAGE  # the language `name` is written in


@dataclass(frozen=True)
class SearchIngredientsDTO:
    query: str | None = None
    category: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class IngredientDTO:
    id: str
    name: LocalizedText  # every language; the HTTP layer picks the viewer's
    description: str | None
    default_category: str | None  # stable code
    category_name: LocalizedText | None  # its display name
