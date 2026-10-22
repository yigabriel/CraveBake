"""
ImageReferences — port to ask "which image URLs does the rest of the application still use?".

Photos are only ever *referenced* by other modules (a recipe photo, an avatar, a
preparation's copy of a step photo). Deleting a file is therefore safe only when
no one references it: a personalization and a preparation both keep the URL of
the original's photo, so removing one photo never proves the file is unused.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ImageReferences(ABC):
    @abstractmethod
    async def urls(self) -> set[str]:
        """Every image URL stored anywhere in the application."""
