"""Pydantic request/response models for authentication endpoints (HTTP boundary only)."""
from pydantic import BaseModel, EmailStr, Field

from app.iam.presentation.http.schemas.user_schemas import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, examples=["SecurePass123"])
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
