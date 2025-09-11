from operetta.ddd.domain.errors import (
    ConflictError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from operetta.ddd.shared.errors import AppBaseException


class ApplicationError(AppBaseException):
    pass


class NotFoundApplicationError(EntityNotFoundError):
    """Application failed to locate a required resource."""

    pass


class AuthorizationFailedError(PermissionDeniedError):
    """Actor is authenticated but is not allowed to perform the action at the
    application process level."""

    pass


class AuthenticationFailedError(PermissionDeniedError):
    """Actor failed to authenticate against application."""

    pass


class InvalidOperationError(ApplicationError):
    """Operation not allowed due to improper invocation or workflow state."""

    pass


class RelatedEntityNotFoundError(ConflictError):
    """Operation failed due to missing related resource/entity (e.g., foreign
    key constraint)."""

    pass


class DependencyUnavailableError(ApplicationError):
    """Some dependency/service the application requires is unavailable."""

    pass


class UnexpectedApplicationError(ApplicationError):
    """Catch-all for non-domain-specific, unexpected errors at the
    orchestration level."""

    pass
