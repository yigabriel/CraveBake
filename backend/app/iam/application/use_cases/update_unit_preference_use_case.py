"""
UpdateUnitPreferenceUseCase.

Lets a user change their global display preference (metric vs US units)
"""
from __future__ import annotations

from app.iam.application.dto.update_unit_preference_dto import UpdateUnitPreferenceDTO
from app.iam.application.dto.user_dto import UserDTO
from app.iam.application.mappers.user_mapper import user_to_dto
from app.iam.domain.exceptions import InvalidTokenError, UserNotFoundError
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.value_objects.unit_system_preference import UnitSystemPreference
from app.iam.domain.value_objects.user_id import UserId
from app.iam.domain.services.token_service import TokenService


class UpdateUnitPreferenceUseCase:
    def __init__(self, user_repository: UserRepository, token_service: TokenService) -> None:
        self._user_repository = user_repository
        self._token_service = token_service

    async def execute(self, access_token: str, dto: UpdateUnitPreferenceDTO) -> UserDTO:

        try: 
            payload = self._token_service.decode_access_token(access_token)
        except Exception as error:  
            raise InvalidTokenError() from error    
        
        user = await self._user_repository.get_by_id(payload.user_id)
        if user is None:
            raise UserNotFoundError(payload.user_id)

        user.change_unit_preference(UnitSystemPreference(dto.preferred_unit_system))
        await self._user_repository.update(user)

        return user_to_dto(user)
