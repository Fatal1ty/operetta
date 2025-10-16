import enum
import logging
from dataclasses import fields
from typing import Any, Iterable, Literal

import aiomisc
import dishka
from dishka.exceptions import NoFactoryError

from operetta.service.base import Service

from .config import SentryServiceConfig
from .providers import SentryServiceConfigProvider

try:
    import sentry_sdk
    from sentry_sdk.client import BaseClient
    from sentry_sdk.integrations.logging import (
        DEFAULT_LEVEL,
        LoggingIntegration,
        ignore_logger,
    )
except Exception as e:
    raise RuntimeError(
        "sentry-sdk is required to run SentryService. Install "
        "with `pip install sentry-sdk` or extras `operetta[sentry]`."
    ) from e

log = logging.getLogger(__name__)


class _S(enum.Enum):
    MISSING = enum.auto()


def _normalize_level(value: int | str | None, default: int) -> int:
    import logging as _logging

    if value is None:
        return default
    if isinstance(value, int):
        return value
    # string level name
    level = _logging.getLevelName(str(value).upper())
    if isinstance(level, int):
        return level
    # fallback
    return default


class SentryService(Service):
    __async_required__: tuple[str, ...] = ("start",)

    def __init__(
        self,
        *,
        dsn: str | None = None,
        enabled: bool | Literal[_S.MISSING] = _S.MISSING,
        capture_log_level: int | str | Literal[_S.MISSING] = _S.MISSING,
        context_log_level: int | str | Literal[_S.MISSING] = _S.MISSING,
        ignore_loggers: Iterable[str] | Literal[_S.MISSING] = _S.MISSING,
        environment: str | Literal[_S.MISSING] = _S.MISSING,
        release: str | Literal[_S.MISSING] = _S.MISSING,
        server_name: str | Literal[_S.MISSING] = _S.MISSING,
        include_local_variables: bool | Literal[_S.MISSING] = _S.MISSING,
        max_breadcrumbs: int | Literal[_S.MISSING] = _S.MISSING,
        shutdown_timeout: float | Literal[_S.MISSING] = _S.MISSING,
        sample_rate: float | Literal[_S.MISSING] = _S.MISSING,
        traces_sample_rate: float | Literal[_S.MISSING] = _S.MISSING,
        ignore_errors: Iterable[str] | Literal[_S.MISSING] = _S.MISSING,
        in_app_include: Iterable[str] | Literal[_S.MISSING] = _S.MISSING,
        in_app_exclude: Iterable[str] | Literal[_S.MISSING] = _S.MISSING,
        send_default_pii: bool | Literal[_S.MISSING] = _S.MISSING,
        debug: bool | Literal[_S.MISSING] = _S.MISSING,
        max_request_body_size: str | Literal[_S.MISSING] = _S.MISSING,
        trace_propagation_targets: (
            Iterable[str] | Literal[_S.MISSING]
        ) = _S.MISSING,
        keep_alive: bool | Literal[_S.MISSING] = _S.MISSING,
        extra_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._config = SentryServiceConfig(
            dsn=dsn,
            enabled=enabled if enabled is not _S.MISSING else None,
            capture_log_level=(
                capture_log_level
                if capture_log_level is not _S.MISSING
                else None
            ),
            context_log_level=(
                context_log_level
                if context_log_level is not _S.MISSING
                else None
            ),
            ignore_loggers=(
                list(ignore_loggers)
                if ignore_loggers is not _S.MISSING
                else None
            ),
            environment=environment if environment is not _S.MISSING else None,
            release=release if release is not _S.MISSING else None,
            server_name=server_name if server_name is not _S.MISSING else None,
            include_local_variables=(
                include_local_variables
                if include_local_variables is not _S.MISSING
                else None
            ),
            max_breadcrumbs=(
                max_breadcrumbs if max_breadcrumbs is not _S.MISSING else None
            ),
            shutdown_timeout=(
                shutdown_timeout
                if shutdown_timeout is not _S.MISSING
                else None
            ),
            sample_rate=sample_rate if sample_rate is not _S.MISSING else None,
            traces_sample_rate=(
                traces_sample_rate
                if traces_sample_rate is not _S.MISSING
                else None
            ),
            ignore_errors=(
                list(ignore_errors)
                if ignore_errors is not _S.MISSING
                else None
            ),
            in_app_include=(
                list(in_app_include)
                if in_app_include is not _S.MISSING
                else None
            ),
            in_app_exclude=(
                list(in_app_exclude)
                if in_app_exclude is not _S.MISSING
                else None
            ),
            send_default_pii=(
                send_default_pii
                if send_default_pii is not _S.MISSING
                else None
            ),
            debug=debug if debug is not _S.MISSING else None,
            max_request_body_size=(
                max_request_body_size
                if max_request_body_size is not _S.MISSING
                else None
            ),
            trace_propagation_targets=(
                list(trace_propagation_targets)
                if trace_propagation_targets is not _S.MISSING
                else None
            ),
            keep_alive=keep_alive if keep_alive is not _S.MISSING else None,
            extra_options=dict(extra_options or {}),
        )
        # Track which fields the user explicitly set (different from defaults)
        self._user_set: set[str] = set()
        for f in fields(SentryServiceConfig):
            if getattr(self._config, f.name) is not None:
                self._user_set.add(f.name)

        self._client: BaseClient | None = None

    async def start(self) -> Any:
        # merge config from DI if available
        try:
            di_cfg = await self.get_dependency(SentryServiceConfig)
        except NoFactoryError:
            di_cfg = None

        if di_cfg is not None:
            # only apply fields not explicitly set by user
            for f in fields(SentryServiceConfig):
                if f.name not in self._user_set:
                    setattr(self._config, f.name, getattr(di_cfg, f.name))

        if self._config.enabled is False:
            log.info("SentryService disabled by config; skipping init")
            return None

        if not self._config.dsn:
            log.warning(
                "SentryService enabled but no DSN provided; skipping init"
            )
            return None

        # logging integration levels
        context_level = _normalize_level(
            self._config.context_log_level, DEFAULT_LEVEL
        )
        event_level = _normalize_level(
            self._config.capture_log_level, logging.ERROR
        )

        integrations = [
            LoggingIntegration(level=context_level, event_level=event_level)
        ]
        for name in self._config.ignore_loggers or []:
            ignore_logger(name)

        options: dict[str, Any] = {
            "dsn": self._config.dsn,
            "environment": self._config.environment,
            "release": self._config.release,
            "server_name": self._config.server_name,
            "include_local_variables": self._config.include_local_variables,
            "max_breadcrumbs": self._config.max_breadcrumbs,
            "shutdown_timeout": self._config.shutdown_timeout,
            "sample_rate": self._config.sample_rate,
            "traces_sample_rate": self._config.traces_sample_rate,
            "ignore_errors": (
                list(self._config.ignore_errors)
                if self._config.ignore_errors
                else None
            ),
            "send_default_pii": self._config.send_default_pii,
            "debug": self._config.debug,
            "max_request_body_size": self._config.max_request_body_size,
            "in_app_include": (
                list(self._config.in_app_include)
                if self._config.in_app_include
                else None
            ),
            "in_app_exclude": (
                list(self._config.in_app_exclude)
                if self._config.in_app_exclude
                else None
            ),
            "integrations": integrations,
            "trace_propagation_targets": (
                list(self._config.trace_propagation_targets)
                if self._config.trace_propagation_targets
                else None
            ),
            "keep_alive": self._config.keep_alive,
        }
        # drop Nones to avoid overriding SDK defaults
        options = {k: v for k, v in options.items() if v is not None}
        # add extra options if any
        options.update(self._config.extra_options)

        # initialize SDK
        sentry_sdk.init(**options)
        self._client = sentry_sdk.Hub.current.client
        log.info("SentryService initialized")
        return None

    async def stop(self, exception: Exception | None = None) -> None:
        if not self._client:
            return
        await self._close_client()

    @aiomisc.threaded
    def _close_client(self):
        if self._client:
            self._client.close()
            self._client = None


class SentryConfigurationService(Service):
    async def start(self) -> Any:
        pass

    async def get_di_providers(self) -> list[dishka.Provider]:
        return [SentryServiceConfigProvider()]
