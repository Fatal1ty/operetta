from __future__ import annotations

from typing import Any, Sequence


class AppError(Exception):
    """Base exception for application, domain, and infrastructure layers.

    Carries optional structured details to be surfaced to clients/logs.
    """

    details: Sequence[Any] = ()

    def __init__(self, *args: Any, details: Sequence[Any] = ()) -> None:
        super().__init__(*args)
        self.details = details or self.details

    def __str__(self) -> str:
        """Always returns a non-empty string for logs/printing.

        Default Exception behaviour makes `str(Exception()) == ''`. Here we
        fall back to the class name when no args were provided.
        """

        if self.args:
            return super().__str__()
        return self.__class__.__name__

    def __repr__(self) -> str:
        if self.args:
            return (
                f"{self.__class__.__name__}({super().__str__()!r}, "
                f"details={self.details!r})"
            )
        return f"{self.__class__.__name__}(details={self.details!r})"


# Domain layer
class DomainError(AppError):
    """Errors representing violations of business rules or domain state."""

    pass


class ValidationError(DomainError):
    """Invalid input/state against business rules or invariants."""

    pass


class ConflictError(DomainError):
    """Domain state prevents the requested action (state/version conflicts)."""

    pass


class NotFoundError(DomainError):
    """Requested domain object/resource not found by identifier or key."""

    pass


class AlreadyExistsError(DomainError):
    """Attempt to create a duplicate or conflicting entity."""

    pass


class PermissionDeniedError(DomainError):
    """Business rules prohibit the action for this actor/entity."""

    pass


# Application layer
class ApplicationError(AppError):
    """Errors at orchestration/use-case level (process, policies)."""

    pass


class InvalidOperationError(ApplicationError):
    """Operation is not allowed due to workflow/state preconditions."""

    pass


class AuthenticationError(ApplicationError):
    """Actor failed to authenticate against the application."""

    pass


class AuthorizationError(ApplicationError):
    """Actor is authenticated but not allowed to perform the action."""

    pass


class RelatedResourceNotFoundError(ApplicationError):
    """Missing related resource required to perform an operation."""

    pass


class DependencyUnavailableError(ApplicationError):
    """Dependency is unreachable or not ready."""

    pass


class DependencyTimeoutError(ApplicationError):
    """Dependency did not respond within expected time."""

    pass


class DependencyFailureError(ApplicationError):
    """Dependency responds but fails or violates its contract."""

    pass


class DependencyThrottledError(ApplicationError):
    """Dependency throttled the request (rate/quota)."""

    pass


# Infrastructure/technical layer
class InfrastructureError(AppError):
    """Technical failures."""

    pass


class DeadlineExceededError(InfrastructureError):
    """Operation exceeded its deadline or timeout (I/O, RPC, local call)."""

    pass


class SubsystemUnavailableError(InfrastructureError):
    """Local subsystem on this host is unavailable (e.g., FS, network)."""

    pass


class StorageIntegrityError(InfrastructureError):
    """Corrupted or unreadable data detected in storage."""

    pass


class TransportIntegrityError(InfrastructureError):
    """Payload/frame corruption detected at transport/protocol level."""

    pass


class SystemResourceLimitExceededError(InfrastructureError):
    """A system resource limit was exceeded (disk, memory, fds, inodes)."""

    pass
