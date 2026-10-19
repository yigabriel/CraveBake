"""Pydantic schemas for the ingredients catalog endpoints."""
from pydantic import BaseModel, Field

from app.shared.presentation.i18n import LocalizedStr


class CreateIngredientRequest(BaseModel):
    # Written in the creator's preferred language; it can be translated later.
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    default_category: str | None = None


class IngredientResponse(BaseModel):
    id: str
    name: LocalizedStr = Field(description="In the signed-in user's preferred language (original if not translated)")
    description: str | None
    default_category: str | None = Field(description="Stable category code, e.g. harina (use it to filter)")
    category_name: LocalizedStr | None = Field(description="The category name in the user's language")
