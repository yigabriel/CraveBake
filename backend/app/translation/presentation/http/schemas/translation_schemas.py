from typing import Literal

from pydantic import BaseModel, Field


class SuggestTranslationsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=255, description="A catalog name, as the user wrote it")
    source: Literal["es", "en"] = Field(description="The language `text` is written in")


class SuggestTranslationsResponse(BaseModel):
    translations: dict[str, str] = Field(
        description="Suggested text for every other language. Only a suggestion: the user reviews it before saving"
    )
