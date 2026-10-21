from app.shared.exceptions.domain_exceptions import ServiceUnavailableError


class TranslationUnavailableError(ServiceUnavailableError):
    """The translation service is not configured, unreachable or refused the request."""

    def __init__(self) -> None:
        super().__init__("Automatic translation is not available right now")
