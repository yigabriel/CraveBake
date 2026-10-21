"""Port: translates a short text between two of the app's languages."""
from __future__ import annotations

from abc import ABC, abstractmethod


class TextTranslator(ABC):
    @abstractmethod
    async def translate(self, text: str, source: str, target: str) -> str:
        """`text` written in `source`, as it reads in `target` (plain text in, plain text out).

        Raises `TranslationUnavailableError` when the service is not configured or fails.
        """
