"""Recommendations-specific domain exceptions, built on the shared exception hierarchy."""
from app.shared.exceptions.domain_exceptions import ConflictError, NotFoundError, ValidationError


class DiscoverySessionNotFoundError(NotFoundError):
    """Also raised for another user's session, so its existence is never revealed."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Discovery session '{identifier}' was not found")


class RecommendedRecipeNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Recipe '{identifier}' was not found")


class SelectedIngredientNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Ingredient '{identifier}' was not found")


class SelectedCategoryNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Recipe category '{identifier}' was not found")


class SelectedTagNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Tag '{identifier}' was not found")


class NoIngredientsAvailableError(ValidationError):
    def __init__(self) -> None:
        super().__init__("Select at least one ingredient, or add ingredients to your pantry first")


class RecipeAlreadySwipedError(ConflictError):
    def __init__(self, recipe_id: str) -> None:
        super().__init__(f"Recipe '{recipe_id}' was already swiped in this session")
