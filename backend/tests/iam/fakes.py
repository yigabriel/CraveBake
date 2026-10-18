"""In-memory test doubles for the IAM ports (repository, hasher, token service)."""
from __future__ import annotations

from app.iam.domain.entities.user import User
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.services.password_hasher import PasswordHasher
from app.iam.domain.services.token_service import TokenPayload, TokenService
from app.iam.domain.value_objects.email import Email
from app.iam.domain.value_objects.hashed_password import HashedPassword
from app.iam.domain.value_objects.plain_password import PlainPassword
from app.iam.domain.value_objects.user_id import UserId


class InMemoryUserRepository(UserRepository):

    def __init__(self) -> None:
        self.users: dict[UserId, User] = {}

    async def add(self, user: User) -> None:
        self.users[user.id] = user

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self.users.get(user_id)

    async def get_by_email(self, email: Email) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    async def exists_by_email(self, email: Email) -> bool:
        return await self.get_by_email(email) is not None

    async def update(self, user: User) -> None:
        self.users[user.id] = user


class FakePasswordHasher(PasswordHasher):
    """Reversible "hash" so tests stay fast; bcrypt has its own test."""

    def hash(self, plain_password: PlainPassword) -> HashedPassword:
        return HashedPassword(f"hashed:{plain_password.value}")

    def verify(self, plain_password: str, hashed_password: HashedPassword) -> bool:
        return hashed_password.value == f"hashed:{plain_password}"


class FakeTokenService(TokenService):

    def generate_access_token(self, user_id: UserId) -> str:
        return f"token:{user_id}"

    def decode_access_token(self, token: str) -> TokenPayload:
        if not token.startswith("token:"):
            raise ValueError("Could not decode token")
        return TokenPayload(user_id=UserId.from_string(token.removeprefix("token:")))


def make_user(
    email: str = "ana@example.com",
    password: str = "Secret123",
    full_name: str = "Ana",
    is_active: bool = True,
) -> User:
    user = User.register(
        email=Email(email),
        hashed_password=FakePasswordHasher().hash(PlainPassword(password)),
        full_name=full_name,
    )
    if not is_active:
        user.deactivate()
    return user
