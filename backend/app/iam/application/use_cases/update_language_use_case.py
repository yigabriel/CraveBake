"""
UpdateLanguageUseCase.

Lets an authenticated user change their preferred display language.
"""
from __future__ import annotations

from app.iam.application.dto.update_language_dto import UpdateLanguageDTO
from app.iam.application.dto.user_dto import UserDTO
from app.iam.application.mappers.user_mapper import user_to_dto
from app.iam.domain.exceptions import UserNotFoundError
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.value_objects.user_id import UserId


class UpdateLanguageUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def execute(self, user_id: str, dto: UpdateLanguageDTO) -> UserDTO:
        user = await self._user_repository.get_by_id(UserId.from_string(user_id))
        if user is None:
            raise UserNotFoundError(user_id)

        user.change_language_preference(dto.preferred_language)
        await self._user_repository.update(user)

        return user_to_dto(user)
