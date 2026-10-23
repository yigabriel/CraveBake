"""
What a video says: its title, its description (the caption) and its transcript.

The transcript is only what the platform itself already has (its own captions): nothing is
transcribed from audio here. A video without them simply has no transcript.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.shared.exceptions.domain_exceptions import NotFoundError, ServiceUnavailableError, ValidationError

# What goes to the model is capped: the cost of an import grows with the text.
MAX_TITLE = 300
MAX_DESCRIPTION = 4000
MAX_TRANSCRIPT = 12000
# Under this the text cannot hold a recipe (a hashtag, a greeting).
MIN_USEFUL_CHARACTERS = 40


class VideoUnavailableError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("That video is private, was removed or cannot be reached")


class NotEnoughTextError(ValidationError):
    def __init__(self) -> None:
        super().__init__("That video has no description or captions to read a recipe from")


class NotARecipeError(ValidationError):
    def __init__(self) -> None:
        super().__init__("We could not find a recipe in that video's text")


class ImportUnavailableError(ServiceUnavailableError):
    def __init__(self) -> None:
        super().__init__("Importing recipes from videos is not available right now")


@dataclass(frozen=True)
class VideoText:
    title: str | None = None
    description: str | None = None
    transcript: str | None = None
    author: str | None = None  # @username or display name, to credit the source
    thumbnail_url: str | None = None  # the platform's cover frame (a signed link that expires)

    @classmethod
    def clean(
        cls,
        title: str | None,
        description: str | None,
        transcript: str | None,
        author: str | None,
        thumbnail_url: str | None = None,
    ) -> "VideoText":
        def tidy(text: str | None, limit: int) -> str | None:
            text = (text or "").strip()
            return text[:limit] or None

        return cls(
            tidy(title, MAX_TITLE),
            tidy(description, MAX_DESCRIPTION),
            tidy(transcript, MAX_TRANSCRIPT),
            tidy(author, 100),
            tidy(thumbnail_url, 2000),
        )

    @property
    def readable_characters(self) -> int:
        return sum(len(part) for part in (self.title, self.description, self.transcript) if part)

    @property
    def is_enough(self) -> bool:
        return self.readable_characters >= MIN_USEFUL_CHARACTERS
