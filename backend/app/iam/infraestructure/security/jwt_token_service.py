"""JWT implementation of the `TokenService` domain service interface."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.iam.domain.services.token_service import TokenPayload, TokenService
from app.iam.domain.value_objects.user_id import UserId

_SUBJECT_CLAIM = "sub"


class JwtTokenService(TokenService):
    def __init__(self, secret_key: str, algorithm: str, expire_minutes: int) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def generate_access_token(self, user_id: UserId) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self._expire_minutes)
        payload = {_SUBJECT_CLAIM: str(user_id), "exp": expires_at}
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except JWTError as error:
            raise ValueError("Could not decode token") from error

        subject = payload.get(_SUBJECT_CLAIM)
        if subject is None:
            raise ValueError("Token is missing subject claim")

        return TokenPayload(user_id=UserId.from_string(subject))
