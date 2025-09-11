from operetta.ddd.shared.errors import AppBaseException


class InfrastructureError(AppBaseException):
    pass


class ResourceUnavailableError(InfrastructureError):
    """Some required underlying resource (disk, file, network) is not available
    — agnostic to protocol."""

    pass


class TimeoutError(InfrastructureError):
    """Operation did not complete within expected timeframe."""

    pass


class DependencyFailureError(InfrastructureError):
    """Failure in a supporting module or external system (e.g., cache fails to
    respond)."""

    pass


class DataCorruptionError(InfrastructureError):
    """Infrastructure detects/receives corrupted or unreadable data."""

    pass


class QuotaExceededError(InfrastructureError):
    """System, user, or resource quota/limit enforced at a technical level is
    exceeded."""

    pass


class UnexpectedInfrastructureError(InfrastructureError):
    """For unexpected or generic technical faults."""

    pass
