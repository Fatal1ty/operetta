from dataclasses import dataclass, field
from typing import Any


@dataclass
class SentryServiceConfig:
    """Configuration for SentryService.

    Mirrors a subset of sentry_sdk.init options and logging integration
    settings. All fields are optional and can be supplied either via
    DI-config or directly into SentryService constructor.
    """

    dsn: str | None = None
    enabled: bool | None = None

    # Logging integration
    capture_log_level: int | str | None = None  # event level
    context_log_level: int | str | None = None  # breadcrumbs level
    ignore_loggers: list[str] | None = None

    # Core SDK options
    environment: str | None = None
    release: str | None = None
    server_name: str | None = None

    include_local_variables: bool | None = None
    max_breadcrumbs: int | None = None
    shutdown_timeout: float | None = None

    # Sampling
    sample_rate: float | None = None
    traces_sample_rate: float | None = None

    # Error filtering and in-app
    ignore_errors: list[str] | None = None
    in_app_include: list[str] | None = None
    in_app_exclude: list[str] | None = None

    # Privacy / debug
    send_default_pii: bool | None = None
    debug: bool | None = None

    # HTTP body and propagation
    max_request_body_size: str | None = None
    trace_propagation_targets: list[str] | None = None

    # Transport tweaks
    keep_alive: bool | None = None

    # Extra passthrough for future extension
    extra_options: dict[str, Any] = field(default_factory=dict)
