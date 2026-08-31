"""
TokenService — interface for issuing/decoding access tokens.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.iam.domain.value_objects.user_id import UserId


@dataclass(frozen=True)
class TokenPayload:
    user_id: UserId


class TokenService(ABC):
    @abstractmethod
    def generate_access_token(self, user_id: UserId) -> str:
        ...

    @abstractmethod
    def decode_access_token(self, token: str) -> TokenPayload:
        ...
