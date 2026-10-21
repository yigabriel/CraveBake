"""
Localized catalog names in the database — written once, used by every catalog.

A catalog table mixes in `LocalizedNameMixin`: a JSONB `names` column
({"es": "Manteca", "en": "Butter"}) plus `name_language` (the language it was
written in, the fallback). Uniqueness lives in per-language expression indexes,
lower(names->>'es') and lower(names->>'en'), created by the migrations.

The helpers below build the queries every catalog repository needs, so
"search in any language" or "is this name taken in any language" never gets
re-implemented per module.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import String, func, or_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.text_search import contains_folded, equals_folded
from app.shared.domain.value_objects.localized_text import SUPPORTED_LANGUAGES, LocalizedText


class LocalizedNameMixin:
    names: Mapped[dict] = mapped_column(JSONB, nullable=False)
    name_language: Mapped[str] = mapped_column(String(2), nullable=False, server_default="en")

    @property
    def localized_name(self) -> LocalizedText:
        return LocalizedText(self.names, original=self.name_language)


def name_columns(name: LocalizedText) -> dict[str, Any]:
    """Column values for a LocalizedText, to build or update a model."""
    return {"names": name.as_dict(), "name_language": name.original}


def _name_in(model: Any, language: str):
    return model.names[language].astext


def name_equals(model: Any, name: str):
    """WHERE clause: `model` is called `name` in any language, ignoring case and accents."""
    return or_(*(equals_folded(_name_in(model, language), name) for language in SUPPORTED_LANGUAGES))


def name_contains(model: Any, text: str):
    """WHERE clause: `text` appears in the name in any language, ignoring case and accents."""
    return or_(*(contains_folded(_name_in(model, language), text) for language in SUPPORTED_LANGUAGES))


def original_name(model: Any):
    """ORDER BY expression: the name as it was written, in whatever language that was."""
    return func.lower(model.names.op("->>")(model.name_language))
