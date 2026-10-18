"""
Maps the User domain entity to the UserDTO exposed to outer layers.

Kept in one place so every use case that needs to return user data shares
the exact same mapping (avoids duplicating this logic across use cases).
"""
from app.iam.application.dto.user_dto import UserDTO
from app.iam.domain.entities.user import User


def user_to_dto(user: User) -> UserDTO:
    return UserDTO(
        id=str(user.id),
        email=str(user.email),
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        preferred_unit_system=user.preferred_unit_system.value,
        is_active=user.is_active,
        preferred_language=user.preferred_language.value,
    )
