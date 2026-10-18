"""DTO for an ingredient category summary."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryDTO:
    name: str
    ingredient_count: int
