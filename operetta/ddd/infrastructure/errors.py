from operetta.ddd.shared.errors import AppBaseException


class InfrastructureError(AppBaseException):
    """Base class for technical failures in the infrastructure layer."""

    pass


class DeadlineExceededError(InfrastructureError):
    """The operation exceeded its deadline or timeout (I/O, RPC, local call)."""

    pass


class DependencyUnavailableError(InfrastructureError):
    """External dependency is unreachable or not ready.

    Includes DNS failure, connect timeout/refused, or TLS handshake
    errors.
    """

    pass


class DependencyFailureError(InfrastructureError):
    """External dependency responds but fails or violates its contract."""

    pass


class SubsystemUnavailableError(InfrastructureError):
    """Local subsystem on this host is unavailable.

    Examples: filesystem/disk not mounted, or local network down.
    """

    pass


class StorageIntegrityError(InfrastructureError):
    """Corrupted or unreadable data detected in storage.

    Examples: checksum mismatch or bad blocks.
    """

    pass


class TransportIntegrityError(InfrastructureError):
    """Payload or frame corruption detected at the transport or protocol level."""

    pass


class SystemResourceLimitExceededError(InfrastructureError):
    """A system resource limit was exceeded.

    Examples: disk space, memory, file descriptors, inode count, or
    storage capacity.
    """

    pass


class DependencyThrottledError(InfrastructureError):
    """An external dependency throttled the request.

    Indicates upstream rate limit or dependency-side quota exhaustion.
    """

    pass


class UnexpectedInfrastructureError(InfrastructureError):
    """Catch-all for unexpected or uncategorized infrastructure faults."""

    pass
