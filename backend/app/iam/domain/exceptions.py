"""IAM-specific domain exceptions, built on the shared exception hierarchy."""
from app.shared.exceptions.domain_exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)


class UserAlreadyExistsError(ConflictError):
    def __init__(self, email: str) -> None:
        super().__init__(f"A user with email '{email}' already exists")


class UserNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"User '{identifier}' was not found")


class InvalidCredentialsError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class InactiveUserError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("This user account is inactive")


class InvalidTokenError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("Invalid or expired authentication token")
