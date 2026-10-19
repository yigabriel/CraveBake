"""
RecipeTag — controlled catalog of recipe attributes (chocolate, sin gluten, navidad...).

Complements the category: a recipe has exactly one category ("what it is":
torta, cupcake...) and any number of tags ("what it is like"). Tags are a
seeded catalog, not free text, so "torta"/"tortas"/"Torta" never split the
same idea into three filters. Each tag belongs to a group, so clients can
lay filters out in sections (sabor, dieta, ...).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId
from app.shared.domain.value_objects.localized_text import LocalizedText


class TagGroup(str, Enum):
    SABOR = "sabor"
    DIETA = "dieta"
    TECNICA = "tecnica"
    TIEMPO = "tiempo"
    CELEBRACIONES = "celebraciones"

    @property
    def label(self) -> LocalizedText:
        return _LABELS[self]


# Fixed by the enum (not data), so they live here rather than in a table.
_LABELS = {
    TagGroup.SABOR: LocalizedText({"es": "Sabor", "en": "Flavor"}),
    TagGroup.DIETA: LocalizedText({"es": "Dieta", "en": "Diet"}),
    TagGroup.TECNICA: LocalizedText({"es": "Técnica y equipo", "en": "Technique & equipment"}),
    TagGroup.TIEMPO: LocalizedText({"es": "Tiempo", "en": "Time"}),
    TagGroup.CELEBRACIONES: LocalizedText({"es": "Celebraciones", "en": "Celebrations"}),
}


@dataclass
class RecipeTag:
    id: RecipeTagId
    name: LocalizedText
    group: TagGroup
