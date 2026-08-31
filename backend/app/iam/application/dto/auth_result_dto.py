"""Output DTO for a successful login: the issued token plus the authenticated user."""
from dataclasses import dataclass

from app.iam.application.dto.user_dto import UserDTO


@dataclass(frozen=True)
class AuthResultDTO:
    access_token: str
    token_type: str
    user: UserDTO
