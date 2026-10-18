"""Preparation-specific domain exceptions, built on the shared exception hierarchy."""
from app.shared.exceptions.domain_exceptions import ConflictError, NotFoundError, ValidationError


class PreparationNotFoundError(NotFoundError):
    """Also raised for another user's preparation, so its existence is never revealed."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Preparation '{identifier}' was not found")


class PreparationRecipeNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Recipe '{identifier}' was not found")


class PreparationStepNotFoundError(NotFoundError):
    def __init__(self, step_number: int) -> None:
        super().__init__(f"Step {step_number} does not exist in this preparation")


class PreparationNotInProgressError(ConflictError):
    def __init__(self, status: str) -> None:
        super().__init__(f"This preparation is already {status}; start a new one to cook again")


class StepHasNoTimerError(ValidationError):
    def __init__(self, step_number: int) -> None:
        super().__init__(f"Step {step_number} has no timer")
