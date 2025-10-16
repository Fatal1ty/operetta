import asyncio
import enum
import logging
from dataclasses import fields
from typing import Any

import dishka
from dishka.exceptions import NoFactoryError

from operetta.service.base import Service

from .config import PrometheusServiceConfig
from .providers import PrometheusServiceConfigProvider

try:
    from prometheus_client import REGISTRY
    from prometheus_client.exposition import (
        CONTENT_TYPE_LATEST,
        generate_latest,
    )
    from prometheus_client.registry import CollectorRegistry
except Exception as e:
    raise RuntimeError(
        "prometheus-client is required to run PrometheusService. "
        "Install with `pip install prometheus-client` or extras "
        "`pip install 'operetta[prometheus]'`."
    ) from e

log = logging.getLogger(__name__)


class Sentinel(enum.Enum):
    MISSING = enum.auto()


MISSING = Sentinel.MISSING


class PrometheusService(Service):
    __async_required__: tuple[str, ...] = ("start",)

    def __init__(
        self,
        *,
        address: str | Sentinel = MISSING,
        port: int | Sentinel = MISSING,
        endpoint: str | Sentinel = MISSING,
        enabled: bool | Sentinel = MISSING,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._config = PrometheusServiceConfig(
            address=(
                address
                if address is not MISSING
                else PrometheusServiceConfig.address
            ),
            port=port if port is not MISSING else PrometheusServiceConfig.port,
            endpoint=(
                endpoint
                if endpoint is not MISSING
                else PrometheusServiceConfig.endpoint
            ),
            enabled=(
                enabled
                if enabled is not MISSING
                else PrometheusServiceConfig.enabled
            ),
        )
        self._user_set: set[str] = set()
        # track explicitly set fields
        if address is not MISSING:
            self._user_set.add("address")
        if port is not MISSING:
            self._user_set.add("port")
        if endpoint is not MISSING:
            self._user_set.add("endpoint")
        if enabled is not MISSING:
            self._user_set.add("enabled")

        self._server: asyncio.AbstractServer | None = None
        self._registry: CollectorRegistry | None = None

    async def start(self) -> Any:  # noqa: C901 - keep explicit
        # Merge config from DI if available
        try:
            di_cfg = await self.get_dependency(PrometheusServiceConfig)
        except NoFactoryError:
            di_cfg = None
        if di_cfg is not None:
            for f in fields(PrometheusServiceConfig):
                if f.name not in self._user_set:
                    setattr(self._config, f.name, getattr(di_cfg, f.name))

        if not self._config.enabled:
            log.info("PrometheusService disabled by config; skipping start")
            return None

        # Normalize endpoint (ensure leading slash)
        if self._config.endpoint and not self._config.endpoint.startswith("/"):
            self._config.endpoint = "/" + self._config.endpoint

        # Try to resolve a registry from DI; fall back to default REGISTRY
        try:
            self._registry = await self.get_dependency(CollectorRegistry)
        except NoFactoryError:
            self._registry = REGISTRY

        self._content_type = CONTENT_TYPE_LATEST
        self._generate_latest = generate_latest

        self._server = await asyncio.start_server(
            self._handle_connection,
            host=self._config.address,
            port=self._config.port,
        )
        sockets = ", ".join(
            str(sock.getsockname()) for sock in self._server.sockets or []
        )
        log.info(
            "PrometheusService started at %s, endpoint=%s",
            sockets,
            self._config.endpoint,
        )
        return None

    async def stop(self, exception: Exception | None = None) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        start_time = self.loop.time()
        peer = writer.get_extra_info("peername")
        if isinstance(peer, tuple) and len(peer) >= 2:
            remote = f"{peer[0]}:{peer[1]}"
        else:
            remote = str(peer) if peer else "-"

        method = "-"
        path = "-"
        client_name = "-"

        try:
            request_data = await reader.readuntil(b"\r\n\r\n")
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            await self._send_response(
                writer,
                400,
                b"Bad Request\n",
                None,
                method,
                path,
                start_time,
                remote,
                client_name,
            )
            return
        # Parse request line and headers
        try:
            header_text = request_data.decode("latin-1", errors="replace")
            lines = header_text.split("\r\n")
            request_line = lines[0]
            method, raw_path, _ = request_line.split(" ", 2)
            path = raw_path.split("?", 1)[0]

            # simple header parsing (case-insensitive)
            headers: dict[str, str] = {}
            for line in lines[1:]:
                if not line:
                    break
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

            # choose best-effort client identifier
            client_name = (
                headers.get("x-client-name")
                or headers.get("x-service-name")
                or headers.get("user-agent")
                or "-"
            )
            # keep log line compact
            if len(client_name) > 200:
                client_name = client_name[:200] + "…"
        except Exception:
            await self._send_response(
                writer,
                400,
                b"Bad Request\n",
                None,
                method,
                path,
                start_time,
                remote,
                client_name,
            )
            return

        # Only GET/HEAD supported
        if method not in ("GET", "HEAD"):
            await self._send_response(
                writer,
                405,
                b"Method Not Allowed\n",
                None,
                method,
                path,
                start_time,
                remote,
                client_name,
            )
            return

        # Accept both with and without trailing slash
        endpoint = self._config.endpoint
        allowed_paths = {endpoint, endpoint.rstrip("/") or "/"}
        if path not in allowed_paths:
            await self._send_response(
                writer,
                404,
                b"Not Found\n",
                None,
                method,
                path,
                start_time,
                remote,
                client_name,
            )
            return

        try:
            assert self._registry
            body = self._generate_latest(self._registry)
        except Exception as e:  # pragma: no cover
            log.exception("Failed to generate prometheus metrics: %s", e)
            await self._send_response(
                writer,
                500,
                b"Internal Server Error\n",
                None,
                method,
                path,
                start_time,
                remote,
                client_name,
            )
            return

        headers = {
            "Content-Type": self._content_type,
            "Content-Length": str(len(body if method == "GET" else b"")),
            "Connection": "close",
        }
        await self._send_response(
            writer,
            200,
            body if method == "GET" else b"",
            headers,
            method,
            path,
            start_time,
            remote,
            client_name,
        )

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        body: bytes,
        headers: dict[str, str] | None,
        method: str,
        path: str,
        start_time: float,
        remote: str,
        client: str,
    ) -> None:
        await self._write_response(writer, status, body, headers)
        duration_ms = (self.loop.time() - start_time) * 1000.0
        log.info(
            "prometheus %s %s -> %d %dB in %.1fms from %s %s",
            method,
            path,
            status,
            len(body),
            duration_ms,
            remote,
            client,
        )

    async def _write_response(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        body: bytes,
        headers: dict[str, str] | None = None,
    ) -> None:
        try:
            reason = {
                200: "OK",
                400: "Bad Request",
                404: "Not Found",
                405: "Method Not Allowed",
                500: "Internal Server Error",
            }.get(status, "OK")
            lines = [f"HTTP/1.1 {status} {reason}\r\n"]
            if headers:
                for k, v in headers.items():
                    lines.append(f"{k}: {v}\r\n")
            if not headers or "Content-Length" not in headers:
                lines.append(f"Content-Length: {len(body)}\r\n")
            if not headers or "Content-Type" not in headers:
                lines.append("Content-Type: text/plain; charset=utf-8\r\n")
            lines.append("\r\n")
            writer.write("".join(lines).encode("latin-1") + body)
            await writer.drain()
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass


class PrometheusConfigurationService(Service):
    async def start(self) -> Any:
        pass

    async def get_di_providers(self) -> list[dishka.Provider]:
        return [PrometheusServiceConfigProvider()]
