"""Pydantic schema for an ingredient category summary."""
from pydantic import BaseModel


class CategoryResponse(BaseModel):
    name: str
    ingredient_count: int
