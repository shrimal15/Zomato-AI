"""Errors shared by later phases. None of these start a model call."""


class AppError(Exception):
    """Base error for recommendation flow failures."""


class CatalogUnavailable(AppError):
    """The local catalog file is missing or cannot be read."""


class EmptyCatalog(AppError):
    """Cleaning produced no restaurants, so requests must not be served."""


class IdentityCollision(AppError):
    """Two different restaurants resolved to the same id."""


class InvalidPreference(AppError):
    """A preference failed validation and must not reach the filter."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors if errors is not None else [message]
