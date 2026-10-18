"""Recipes-specific domain exceptions, built on the shared exception hierarchy."""
from app.shared.exceptions.domain_exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


class RecipeNotFoundError(NotFoundError):
    """Also raised for private recipes of other users, so their existence is never revealed."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Recipe '{identifier}' was not found")


class RecipeAccessDeniedError(ForbiddenError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"You are not allowed to modify recipe '{identifier}'")


class RecipeCategoryNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Recipe category '{identifier}' was not found")


class RecipeTagNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Tag '{identifier}' was not found")


class DifficultyNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Difficulty '{identifier}' was not found")


class RecipeStepNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Step '{identifier}' was not found in this recipe")


class RecipePhotoNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Photo '{identifier}' was not found in this recipe")


class ReferencedIngredientNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Ingredient '{identifier}' was not found")


class ReferencedUnitNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Unit '{identifier}' was not found")


class ReferencedEquipmentNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Equipment '{identifier}' was not found")


class CoverPhotoLimitExceededError(ConflictError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"A recipe cannot have more than {limit} cover photos")


class StepPhotoAlreadyExistsError(ConflictError):
    def __init__(self, step_id: str) -> None:
        super().__init__(f"Step '{step_id}' already has a photo; remove it first")


class CannotPersonalizePersonalizationError(ValidationError):
    def __init__(self) -> None:
        super().__init__("A personalized recipe cannot be personalized again; personalize the original instead")


class PersonalizationMustBePrivateError(ValidationError):
    def __init__(self) -> None:
        super().__init__("A personalized recipe is always private and cannot be published")
