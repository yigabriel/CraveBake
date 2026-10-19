"""
Choosing the viewer's language for catalog names — once, at the HTTP edge.

Application DTOs carry `LocalizedText` (every language). A response schema
declares the field as `LocalizedStr`; the router validates with
`context=language_context(user)`, and every LocalizedStr in the response tree
(nested models and pages included) becomes the text in that language, falling
back to the original. A plain `str` passes through untouched, so catalogs can
move to LocalizedText one at a time.
"""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import BeforeValidator, ValidationInfo

from app.shared.domain.value_objects.localized_text import LocalizedText


def _localize(value: Any, info: ValidationInfo) -> Any:
    if isinstance(value, LocalizedText):
        language = (info.context or {}).get("language")
        return value.in_(language)
    return value


LocalizedStr = Annotated[str, BeforeValidator(_localize)]


def language_context(user: Any) -> dict[str, str]:
    """Validation context for a response, from the signed-in user's preference."""
    return {"language": getattr(user, "preferred_language", None) or "es"}
