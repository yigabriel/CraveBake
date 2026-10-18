"""Pydantic schemas for the ingredients catalog endpoints."""
from pydantic import BaseModel, Field


class CreateIngredientRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    default_category: str | None = None


class IngredientResponse(BaseModel):
    id: str
    name: str
    description: str | None
    default_category: str | None
