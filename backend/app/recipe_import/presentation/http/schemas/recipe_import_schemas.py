"""Pydantic schemas of the recipe-import endpoint."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from app.shared.presentation.i18n import LocalizedStr


class ImportRecipeRequest(BaseModel):
    url: str = Field(min_length=1, max_length=500, description="Link to a TikTok video or an Instagram Reel")


class DraftCatalogItemResponse(BaseModel):
    id: str
    name: LocalizedStr
    abbreviation: str | None = None


class DraftIngredientResponse(BaseModel):
    raw_name: str = Field(description="The ingredient as the video says it")
    ingredient: DraftCatalogItemResponse | None = Field(description="The catalog ingredient it was matched to; null: the person must pick or create one")
    quantity: Decimal | None
    unit: DraftCatalogItemResponse | None
    notes: str | None
    section: str | None


class DraftStepResponse(BaseModel):
    instructions: str
    title: str | None
    timer_minutes: Decimal | None
    section: str | None


class WhatWasReadResponse(BaseModel):
    title: bool
    description: bool
    transcript: bool = Field(description="False when the video has no captions of its own: the recipe was read from its title and description")


class RecipeDraftResponse(BaseModel):
    """A draft to review. Nothing has been saved: it is saved through POST /recipes like any other recipe."""

    title: str
    description: str | None
    servings: int | None
    prep_time_minutes: int | None
    source_url: str = Field(description="The cleaned link: use it as the recipe's video_url")
    platform: str
    author: str | None
    read: WhatWasReadResponse
    ingredients: list[DraftIngredientResponse]
    steps: list[DraftStepResponse]
    equipment: list[DraftCatalogItemResponse] = Field(description="Catalog equipment the text uses or implies; empty when it names none")
    category: DraftCatalogItemResponse | None = Field(description="The recipe category that fits, from the catalog")
    difficulty: DraftCatalogItemResponse | None = Field(description="Always the middle difficulty: a video's text cannot say how hard a recipe is")
    cover_url: str | None = Field(
        description="Our stored copy of the video's cover frame (the creator's image): add it as a cover once the recipe exists. Null when it could not be copied"
    )
