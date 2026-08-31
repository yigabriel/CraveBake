"""bcrypt implementation of the `PasswordHasher` domain service interface."""
from __future__ import annotations

from passlib.context import CryptContext

from app.iam.domain.services.password_hasher import PasswordHasher
from app.iam.domain.value_objects.hashed_password import HashedPassword
from app.iam.domain.value_objects.plain_password import PlainPassword

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, plain_password: PlainPassword) -> HashedPassword:
        return HashedPassword(_pwd_context.hash(plain_password.value))

    def verify(self, plain_password: str, hashed_password: HashedPassword) -> bool:
        return _pwd_context.verify(plain_password, hashed_password.value)
