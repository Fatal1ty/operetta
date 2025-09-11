from operetta.ddd.shared.errors import AppBaseException


class DomainError(AppBaseException):
    pass


class ValidationError(DomainError):
    """Raised on business rule or invariant violation; e.g., invalid
    input/state for a domain object."""

    pass


class ConflictError(DomainError):
    """Domain entity/resources in a state that prevents the intended action
    (e.g., state transition not allowed, stale data, or versioning
    conflict)."""

    pass


class EntityNotFoundError(DomainError):
    """Domain object/resource cannot be found by identifier or key."""

    pass


class EntityExistsError(DomainError):
    """Attempt to create a duplicate or conflicting entity."""

    pass


class PermissionDeniedError(DomainError):
    """The business rules prohibit a requested action for this actor/entity."""

    pass


class UnexpectedDomainError(DomainError):
    """A catch-all for truly unexpected domain-layer conditions not fitting the
    above."""

    pass
