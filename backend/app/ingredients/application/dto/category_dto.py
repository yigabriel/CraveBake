"""DTO for an ingredient category summary."""
from dataclasses import dataclass
from app.shared.domain.value_objects.localized_text import LocalizedText


@dataclass(frozen=True)
class CategoryDTO:
    name: str  # stable code, e.g. "harina" (used in /categories/{name}/ingredients)
    label: LocalizedText
    ingredient_count: int
