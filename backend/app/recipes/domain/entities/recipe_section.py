"""
RecipeSection — a named group of a recipe ("Masa choux", "Manjar", "Cobertura").

The same section groups ingredient lines *and* steps, so the name lives here
once instead of being repeated on every line. Sections are owned by the
`Recipe` aggregate: they are created when a line names one and dropped when
no line uses them any more. Names are unique per recipe, ignoring case.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.recipes.domain.value_objects.recipe_section_id import RecipeSectionId
from app.shared.exceptions.domain_exceptions import ValidationError

MAX_SECTION_NAME_LENGTH = 100
MAX_SECTIONS = 20


def clean_section_name(name: str | None) -> str | None:
    """Trimmed, single-spaced name; None for a blank one (= the line has no section)."""
    cleaned = " ".join((name or "").split())
    if not cleaned:
        return None
    if len(cleaned) > MAX_SECTION_NAME_LENGTH:
        raise ValidationError(f"A section name cannot exceed {MAX_SECTION_NAME_LENGTH} characters")
    return cleaned


def section_key(name: str) -> str:
    """What makes two names the same section: "Masa Choux" and "masa choux" are one."""
    return name.casefold()


def check_grouped(names: list[str | None]) -> None:
    """Lines are listed without section first, then each section's lines together.

    This is what lets every client render a heading each time the section
    changes, with no reordering of its own.
    """
    seen: set[str] = set()
    previous: str | None = None
    in_sections = False
    for name in names:
        if name is None:
            if in_sections:
                raise ValidationError("Lines without a section must be listed before the sections")
            continue
        key = section_key(name)
        if key != previous and key in seen:
            raise ValidationError(f"The lines of section '{name}' must be listed together")
        seen.add(key)
        previous = key
        in_sections = True


@dataclass
class RecipeSection:
    id: RecipeSectionId
    name: str

    def __post_init__(self) -> None:
        cleaned = clean_section_name(self.name)
        if cleaned is None:
            raise ValidationError("A section name cannot be empty")
        self.name = cleaned

    @property
    def key(self) -> str:
        return section_key(self.name)
