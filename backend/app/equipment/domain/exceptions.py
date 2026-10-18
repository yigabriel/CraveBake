"""Equipment-specific domain exceptions, built on the shared exception hierarchy."""
from app.shared.exceptions.domain_exceptions import ConflictError, NotFoundError


class EquipmentNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Equipment '{identifier}' was not found")


class EquipmentAlreadyExistsError(ConflictError):
    def __init__(self, name: str) -> None:
        super().__init__(f"An equipment item named '{name}' already exists")
