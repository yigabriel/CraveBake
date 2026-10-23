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
from app.recipe_import.domain.services.ports import (
    CatalogCategory,
    CatalogDifficulty,
    CatalogEquipment,
    CatalogIngredient,
    CatalogUnit,
    CoverImageStore,
    ExtractionCatalog,
    ImportCatalog,
    RecipeExtractor,
    VideoTextSource,
)
from app.recipe_import.domain.source_url import parse_source_url
from app.recipe_import.domain.video_text import NotARecipeError, NotEnoughTextError
from app.shared.domain.text_folding import fold, is_same_name

T = TypeVar("T")


class ImportRecipeFromVideoUseCase:
    def __init__(
        self,
        source: VideoTextSource,
        extractor: RecipeExtractor,
        catalog: ImportCatalog,
        covers: CoverImageStore | None = None,
    ) -> None:
        self._source = source
        self._extractor = extractor
        self._catalog = catalog
        self._covers = covers

    async def execute(self, dto: ImportRecipeDTO) -> RecipeDraftDTO:
        source = parse_source_url(dto.url)
        text = await self._source.fetch(source)
        if not text.is_enough:
            raise NotEnoughTextError()

        ingredients = await self._catalog.ingredients()
        units = await self._catalog.units()
        equipment = await self._catalog.equipment()
        categories = await self._catalog.categories()
        difficulties = await self._catalog.difficulties()
        extracted = await self._extractor.extract(
            text,
            ExtractionCatalog(
                ingredients=[item.name.text for item in ingredients],
                units=[unit.abbreviation for unit in units],
                equipment=[item.name.text for item in equipment],
                categories=[item.name.text for item in categories],
            ),
        )
        if not extracted.is_recipe or not (extracted.ingredients or extracted.steps):
            raise NotARecipeError()

        # Only once it is a recipe: no copy is made for a video that will not become one.
        cover_url = None
        if self._covers is not None and text.thumbnail_url and dto.user_id:
            cover_url = await self._covers.store(text.thumbnail_url, dto.user_id)

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
            equipment=_match_equipment(extracted.equipment, equipment),
            category=_match_category(extracted.category, categories),
            difficulty=_middle_difficulty(difficulties),
            cover_url=cover_url,
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


def _find(wanted: str | None, items: list, name_of=lambda item: item.name):
    """The catalog item called `wanted` (or one of its synonyms) in any language; None if the model made it up."""
    if not wanted:
        return None
    return next((item for item in items if any(is_same_name(name, wanted) for name in name_of(item).as_dict().values())), None)


def _match_equipment(names: list[str], catalog: list[CatalogEquipment]) -> list[DraftCatalogItemDTO]:
    """Only tools that really are in the catalog, each once, in the order the model gave them.

    A recipe can only list catalog equipment, so a tool the model invented (or that is not in the
    catalog) is left out rather than guessed at.
    """
    matched: dict[str, DraftCatalogItemDTO] = {}
    for name in names:
        item = _find(name, catalog)
        if item is not None:
            matched.setdefault(item.id, DraftCatalogItemDTO(id=item.id, name=item.name))
    return list(matched.values())


def _match_category(name: str | None, catalog: list[CatalogCategory]) -> DraftCatalogItemDTO | None:
    item = _find(name, catalog)
    return DraftCatalogItemDTO(id=item.id, name=item.name) if item else None


def _middle_difficulty(catalog: list[CatalogDifficulty]) -> DraftCatalogItemDTO | None:
    """The middle level ("intermediate" in the seeded catalog): the text of a video cannot tell how hard a recipe is."""
    if not catalog:
        return None
    item = sorted(catalog, key=lambda difficulty: difficulty.level_order)[len(catalog) // 2]
    return DraftCatalogItemDTO(id=item.id, name=item.name)
