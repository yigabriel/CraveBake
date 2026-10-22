"""
ImportRecipeFromVideoUseCase — turns a TikTok / Reel link into a recipe *draft*.

    link -> the video's text (title, description, captions) -> the model reads it -> draft

Nothing is saved. The draft goes back to the person, who checks it in the normal recipe
editor and saves it there, so every rule of a real recipe (ownership, limits, validation)
still applies to it. The video text is untrusted: the model's answer is only ever data that
is validated here and shown for review, never instructions that anything follows.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from app.recipe_import.application.dto.recipe_draft_dto import (
    DraftCatalogItemDTO,
    DraftIngredientDTO,
    DraftStepDTO,
    ImportRecipeDTO,
    RecipeDraftDTO,
    WhatWasReadDTO,
)
from app.recipe_import.domain.extracted_recipe import ExtractedIngredient, ExtractedStep
from app.recipe_import.domain.services.ports import CatalogIngredient, CatalogUnit, ImportCatalog, RecipeExtractor, VideoTextSource
from app.recipe_import.domain.source_url import parse_source_url
from app.recipe_import.domain.video_text import NotARecipeError, NotEnoughTextError
from app.shared.domain.text_folding import fold, is_same_name

T = TypeVar("T")


class ImportRecipeFromVideoUseCase:
    def __init__(self, source: VideoTextSource, extractor: RecipeExtractor, catalog: ImportCatalog) -> None:
        self._source = source
        self._extractor = extractor
        self._catalog = catalog

    async def execute(self, dto: ImportRecipeDTO) -> RecipeDraftDTO:
        source = parse_source_url(dto.url)
        text = await self._source.fetch(source)
        if not text.is_enough:
            raise NotEnoughTextError()

        ingredients = await self._catalog.ingredients()
        units = await self._catalog.units()
        extracted = await self._extractor.extract(
            text,
            ingredient_names=[ingredient.name.text for ingredient in ingredients],
            unit_abbreviations=[unit.abbreviation for unit in units],
        )
        if not extracted.is_recipe or not (extracted.ingredients or extracted.steps):
            raise NotARecipeError()

        return RecipeDraftDTO(
            title=extracted.title or text.title or "",
            description=extracted.description,
            servings=extracted.servings,
            prep_time_minutes=extracted.prep_time_minutes,
            source_url=source.url,
            platform=source.platform.value,
            author=text.author,
            read=WhatWasReadDTO(title=bool(text.title), description=bool(text.description), transcript=bool(text.transcript)),
            ingredients=[_ingredient(line, ingredients, units) for line in _grouped(extracted.ingredients, lambda line: line.section)],
            steps=[_step(step) for step in _grouped(extracted.steps, lambda step: step.section)],
        )


def _grouped(items: list[T], section_of: Callable[[T], str | None]) -> list[T]:
    """Lines without a section first, then each section's lines together, in order of first appearance.

    A recipe is stored that way (see `Recipe`); the model may interleave them, so it is fixed here.
    """
    order: dict[str, int] = {}
    for item in items:
        section = section_of(item)
        if section is not None:
            order.setdefault(fold(section), len(order))
    return sorted(items, key=lambda item: -1 if section_of(item) is None else order[fold(section_of(item))])  # stable


def _ingredient(line: ExtractedIngredient, catalog: list[CatalogIngredient], units: list[CatalogUnit]) -> DraftIngredientDTO:
    return DraftIngredientDTO(
        raw_name=line.name,
        ingredient=_match_ingredient(line, catalog),
        quantity=line.quantity,
        unit=_match_unit(line.unit, units),
        notes=line.notes,
        section=line.section,
    )


def _match_ingredient(line: ExtractedIngredient, catalog: list[CatalogIngredient]) -> DraftCatalogItemDTO | None:
    """The model picked from the catalog list: believe it only if the pick really is a catalog name.

    An invented name (or one that is not in the catalog) leaves the line unmatched, so the person
    chooses; the catalog is never guessed at. The video's own wording is tried as a second chance.
    """
    for wanted in filter(None, (line.catalog_name, line.name)):
        for item in catalog:
            if any(is_same_name(name, wanted) for name in item.name.as_dict().values()):
                return DraftCatalogItemDTO(id=item.id, name=item.name)
    return None


def _match_unit(abbreviation: str | None, units: list[CatalogUnit]) -> DraftCatalogItemDTO | None:
    if not abbreviation:
        return None
    wanted = abbreviation.strip().lower()
    unit = next((unit for unit in units if unit.abbreviation.lower() == wanted), None)
    return DraftCatalogItemDTO(id=unit.id, name=unit.name, abbreviation=unit.abbreviation) if unit else None


def _step(step: ExtractedStep) -> DraftStepDTO:
    return DraftStepDTO(instructions=step.instructions, title=step.title, timer_minutes=step.timer_minutes, section=step.section)
