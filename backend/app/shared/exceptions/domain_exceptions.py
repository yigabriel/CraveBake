"""
Base exception hierarchy shared by every bounded context.

Domain and Application layers raise these (or module-specific subclasses)
instead of HTTPException, so they stay completely framework-agnostic.
Presentation is the only layer that knows how to translate them into HTTP
responses (see `exception_handlers.py`).
"""


class DomainError(Exception):
    """Base class for all domain/application errors in the system."""


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist."""


class ConflictError(DomainError):
    """Raised when an operation conflicts with the current state (e.g. duplicate)."""


class ValidationError(DomainError):
    """Raised when a domain invariant or input rule is violated."""


class UnauthorizedError(DomainError):
    """Raised when credentials are missing, invalid, or expired."""


class ForbiddenError(DomainError):
    """Raised when an authenticated user cannot perform an action on a resource."""

class InvalidCredentialsException(UnauthorizedError):
    """Raised when the provided credentials are invalid."""
