"""Portfolio-specific domain exceptions, built on the shared exception hierarchy."""
from app.shared.exceptions.domain_exceptions import NotFoundError, ValidationError


class PortfolioRecipeNotFoundError(NotFoundError):
    """Also raised for private or deleted recipes, so their existence is never revealed."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Recipe '{identifier}' was not found")


class CannotSaveOwnRecipeError(ValidationError):
    def __init__(self) -> None:
        super().__init__("Your own recipes are already part of your portfolio; only other users' public recipes can be saved")
