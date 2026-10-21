"""
LocalizedText — a short text (a catalog name) written in one or more languages.

Shared kernel: every catalog (ingredients now; equipment, categories, tags,
units next) names its items with it, so "the name in this language, or the
original one if it was never translated" is written exactly once.

The domain stores all languages and never knows who is looking: choosing the
viewer's language is a presentation concern (see app.shared.presentation.i18n).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from app.shared.exceptions.domain_exceptions import ValidationError

SUPPORTED_LANGUAGES = ("es", "en")
DEFAULT_LANGUAGE = "en"


@dataclass(frozen=True)
class LocalizedText:
    # language -> text. `original` is the language it was first written in: the fallback.
    values: Mapping[str, str] = field(default_factory=dict)
    original: str = DEFAULT_LANGUAGE

    def __post_init__(self) -> None:
        cleaned = {}
        for language, text in self.values.items():
            if language not in SUPPORTED_LANGUAGES:
                raise ValidationError(f"Unsupported language: {language}")
            text = (text or "").strip()
            if text:
                cleaned[language] = text
        if self.original not in cleaned:
            raise ValidationError("A name cannot be empty")
        # Frozen all the way down: nobody mutates a name behind the entity's back.
        object.__setattr__(self, "values", MappingProxyType(cleaned))

    @classmethod
    def of(cls, text: str, language: str = DEFAULT_LANGUAGE) -> "LocalizedText":
        return cls({language: text}, original=language)

    @classmethod
    def written(cls, text: str, language: str, translations: Mapping[str, str] | None = None) -> "LocalizedText":
        """A name written in `language`, together with the translations the author reviewed.

        A blank translation means "not translated": that language falls back to the original.
        """
        reviewed = {lang: translated for lang, translated in (translations or {}).items() if (translated or "").strip()}
        if language in reviewed:
            raise ValidationError("The translations cannot include the language the name was written in")
        return cls({language: text, **reviewed}, original=language)

    def in_(self, language: str | None) -> str:
        """The text in `language`, or in the original language when it has no translation."""
        return self.values.get(language or self.original) or self.values[self.original]

    @property
    def text(self) -> str:
        """The text as it was originally written."""
        return self.values[self.original]

    def with_translation(self, language: str, text: str) -> "LocalizedText":
        return LocalizedText({**self.values, language: text}, original=self.original)

    def all_texts(self) -> tuple[str, ...]:
        return tuple(self.values.values())

    def as_dict(self) -> dict[str, str]:
        """language -> text, e.g. for a JSONB column (the original language is stored apart)."""
        return dict(self.values)

    def __str__(self) -> str:
        return self.text
