from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuggestTranslationsDTO:
    text: str
    source: str  # the language `text` is written in
