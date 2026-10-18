from pydantic import BaseModel, Field


class ChangePasswordDTO(BaseModel):
    # Only non-empty: it may predate the current strength rules.
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)