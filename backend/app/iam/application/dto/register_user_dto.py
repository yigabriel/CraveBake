"""Input DTO for RegisterUser"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterUserDTO:
    email: str
    password: str
    full_name: str
    preferred_language: str | None = None  # None: the domain default
