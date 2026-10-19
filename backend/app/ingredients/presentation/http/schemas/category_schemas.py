"""Pydantic schema for an ingredient category summary."""
from pydantic import BaseModel
from app.shared.presentation.i18n import LocalizedStr


class CategoryResponse(BaseModel):
    name: str  # stable code
    label: LocalizedStr
    ingredient_count: int
