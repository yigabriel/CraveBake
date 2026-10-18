"""Ingredients-specific domain exceptions, built on the shared exception hierarchy."""
from app.shared.exceptions.domain_exceptions import ConflictError, NotFoundError, ValidationError


class IngredientNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Ingredient '{identifier}' was not found")


class IngredientAlreadyExistsError(ConflictError):
    def __init__(self, name: str) -> None:
        super().__init__(f"An ingredient named '{name}' already exists")


class UnitNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Unit '{identifier}' was not found")


class UserIngredientNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Pantry item '{identifier}' was not found")


class ConversionNotAvailableError(ValidationError):
    def __init__(self, from_unit: str, to_unit: str) -> None:
        super().__init__(
            f"Cannot convert from '{from_unit}' to '{to_unit}' without an ingredient-specific conversion"
        )
