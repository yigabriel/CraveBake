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


class TagGroup(str, Enum):
    SABOR = "sabor"
    DIETA = "dieta"
    TECNICA = "tecnica"
    TIEMPO = "tiempo"
    CELEBRACIONES = "celebraciones"

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS = {
    TagGroup.SABOR: "Sabor",
    TagGroup.DIETA: "Dieta",
    TagGroup.TECNICA: "Técnica y equipo",
    TagGroup.TIEMPO: "Tiempo",
    TagGroup.CELEBRACIONES: "Celebraciones",
}


@dataclass
class RecipeTag:
    id: RecipeTagId
    name: str
    group: TagGroup
