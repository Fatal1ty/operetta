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


# Infrastructure/technical layer
class InfrastructureError(AppError):
    """Technical failures in external dependencies or local subsystems."""

    pass


class DeadlineExceededError(InfrastructureError):
    """Operation exceeded its deadline or timeout (I/O, RPC, local call)."""

    pass


class DependencyUnavailableError(InfrastructureError):
    """External dependency is unreachable or not ready."""

    pass


class DependencyFailureError(InfrastructureError):
    """External dependency responds but fails or violates its contract."""

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


class DependencyThrottledError(InfrastructureError):
    """An external dependency throttled the request (rate/quota)."""

    pass
