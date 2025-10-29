# NOTE ON THIRD-PARTY CODE AND MODIFICATIONS
#
# Portions of this file are adapted from the aiomisc project available at:
# https://github.com/aiokitchen/aiomisc
#
# The original work is licensed under the MIT License. This modified file
# includes attribution and a summary of changes. See the root NOTICE file for
# the full MIT license text and attribution details.
#
# Summary of local changes compared to the original aiomisc implementation:
# - Integrated with Dishka DI (setup_dishka, container handling).
# - Added OpenAPI spec rebuild and static docs serving/customization.
# - Added optional configuration merge from AIOHTTPServiceConfig.
# - Adjusted runner kwargs defaults and handler cancellation wiring.
# - Minor refactoring and typing tweaks (RunnerKwargsType alias) to fit the
#   Operetta codebase conventions.

import asyncio
import logging
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

import aiohttp
import dishka
from aiohttp.typedefs import Middleware
from aiohttp.web import Application, AppRunner, BaseRunner, SockSite
from aiohttp.web_log import AccessLogger
from aiohttp.web_routedef import RouteDef
from aiomisc.utils import bind_socket
from dishka.exceptions import NoFactoryError
from dishka.integrations.aiohttp import setup_dishka

from operetta.integrations.aiohttp.config import AIOHTTPServiceConfig
from operetta.integrations.aiohttp.middlewares import (
    ddd_errors_middleware,
    unhandled_error_middleware,
)
from operetta.integrations.aiohttp.openapi.builder import rebuild_spec
from operetta.integrations.aiohttp.providers import (
    AIOHTTPServiceConfigProvider,
)
from operetta.integrations.aiohttp.route_processing import (
    process_route,
)
from operetta.service.base import Service

log = logging.getLogger(__name__)


RunnerKwargsType = Mapping[str, Any] | Iterable[tuple[str, Any]]


def copy_and_patch_html(src: Path, dst: Path, static_prefix: str):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    with open(dst) as f:
        html = f.read()
    html = html.replace(
        "/static/openapi/openapi.yaml",
        f"{static_prefix}openapi/openapi.yaml",
    )
    with open(dst, "w") as f:
        f.write(html)


class AIOHTTPService(Service):
    __async_required__: tuple[str, ...] = (
        "start",
        "create_application",
    )

    site: SockSite
    runner: BaseRunner
    handler_cancellation: bool = True

    def __init__(
        self,
        routes: Iterable[RouteDef] = (),
        address: str | None = None,
        port: int | None = None,
        middlewares: Iterable[Middleware] = (),
        system_middlewares: Iterable[Middleware] = (
            unhandled_error_middleware,
            ddd_errors_middleware,
        ),
        static_endpoint_prefix: str = "/static/",
        static_files_root: Path | str | None = None,
        docs_default_path: str = "/docs",
        docs_swagger_path: str = "/docs/swagger",
        docs_redoc_path: str = "/docs/redoc",
        docs_title: str = "API",
        docs_servers: Sequence[str] = ("http://127.0.0.1:8080",),
        docs_default_type: Literal["swagger", "redoc", None] = "swagger",
        docs_remove_path_prefix: str | None = None,
        docs_tag_descriptions: dict[str, str] | None = None,
        docs_tag_groups: dict[str, list[str]] | None = None,
        shutdown_timeout: int = 5,
        handler_cancellation: bool = handler_cancellation,
        runner_kwargs: RunnerKwargsType | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._routes = routes
        self._address = address
        self._port = port
        self._middlewares = [*system_middlewares, *middlewares]
        self._docs_default_path = docs_default_path
        self._docs_swagger_path = docs_swagger_path
        self._docs_redoc_path = docs_redoc_path
        self._static_endpoint_prefix = static_endpoint_prefix
        self._static_files_root: Path | None
        if static_files_root is not None:
            self._static_files_root = Path(static_files_root)
        else:
            self._static_files_root = None
        self._docs_title = docs_title
        self._docs_servers = docs_servers
        self._docs_default_type = docs_default_type
        self._docs_remove_path_prefix = docs_remove_path_prefix
        self._docs_tag_descriptions = docs_tag_descriptions
        self._docs_tag_groups = docs_tag_groups

        self._kwargs = kwargs

        self.shutdown_timeout = shutdown_timeout

        self.runner_kwargs: dict[str, Any] = dict(runner_kwargs or {})
        self.runner_kwargs.setdefault("access_log_class", AccessLogger)
        self.runner_kwargs.setdefault(
            "access_log_format", AccessLogger.LOG_FORMAT
        )
        self.runner_kwargs.setdefault(
            "handler_cancellation", handler_cancellation
        )

        self._app_ready = asyncio.Event()

    async def start(self) -> Any:
        # Optionally merge config from DI if available
        cfg = None
        try:
            cfg = await self.get_dependency(AIOHTTPServiceConfig)
        except NoFactoryError:  # no config provider present in DI
            cfg = None

        if cfg is not None:
            # Apply server bind options only if not provided via __init__
            if self._address is None:
                self._address = cfg.address
            if self._port is None:
                self._port = cfg.port

            # Prefer values passed to __init__; override only defaults
            if self._static_endpoint_prefix == "/static/":
                self._static_endpoint_prefix = cfg.static_endpoint_prefix
            if self._static_files_root is None:
                if cfg.static_files_root is not None:
                    self._static_files_root = Path(cfg.static_files_root)
                else:
                    self._static_files_root = Path(tempfile.mkdtemp())
            if self._docs_default_path == "/docs":
                self._docs_default_path = cfg.docs_default_path
            if self._docs_swagger_path == "/docs/swagger":
                self._docs_swagger_path = cfg.docs_swagger_path
            if self._docs_redoc_path == "/docs/redoc":
                self._docs_redoc_path = cfg.docs_redoc_path
            if self._docs_title == "API":
                self._docs_title = cfg.docs_title
            if tuple(self._docs_servers) == ("http://127.0.0.1:8080",):
                self._docs_servers = cfg.docs_servers
            if self._docs_default_type == "swagger":
                self._docs_default_type = cfg.docs_default_type
            if self._docs_remove_path_prefix is None:
                self._docs_remove_path_prefix = cfg.docs_remove_path_prefix
            if self._docs_tag_descriptions is None:
                self._docs_tag_descriptions = cfg.docs_tag_descriptions
            if self._docs_tag_groups is None:
                self._docs_tag_groups = cfg.docs_tag_groups

        if not (self._address and self._port):
            raise RuntimeError(
                'You should pass socket "address" and "port" couple'
            )

        self.socket = bind_socket(
            address=self._address,
            port=self._port,
            proto_name="http",
        )

        if hasattr(self, "runner"):
            raise RuntimeError("Can not start twice")

        application = await self.create_application()
        self.runner = await self.make_runner(application)
        await self.runner.setup()

        self.site = await self.create_site()
        await self.site.start()

    async def create_application(self) -> Application:
        app = Application(middlewares=self._middlewares)
        system_routes = self._get_system_routes()
        app.add_routes(system_routes)
        new_routes = []
        for route in self._routes:
            new_routes.append(process_route(route))
        self._routes = new_routes
        app.add_routes(self._routes)

        if self._static_files_root is not None:
            spec_path = Path(self._static_files_root) / "openapi/openapi.yaml"
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            rebuild_spec(
                routes=self._routes,  # type: ignore[arg-type]
                spec_path=spec_path,
                title=self._docs_title,
                servers=self._docs_servers,
                tag_descriptions=self._docs_tag_descriptions,
                tag_groups=self._docs_tag_groups,
                remove_path_prefix=self._docs_remove_path_prefix,
            )
            app.router.add_static(
                prefix=self._static_endpoint_prefix,
                path=self._static_files_root,
            )
        await self._setup_di(app)
        return app

    async def create_site(self) -> SockSite:
        if getattr(self, "runner", None) is None:
            raise RuntimeError("runner already created")

        return SockSite(self.runner, self.socket)

    async def make_runner(self, application: Application) -> AppRunner:
        return AppRunner(
            application,
            shutdown_timeout=self.shutdown_timeout,
            **self.runner_kwargs,
        )

    async def stop(self, exception: Exception | None = None) -> None:
        with suppress(AttributeError):
            try:
                if self.site:
                    await self.site.stop()
            finally:
                if hasattr(self, "runner"):
                    await self.runner.cleanup()

    def _get_system_routes(self) -> Iterable[RouteDef]:
        """Return system routes."""
        return [
            *self._get_doc_routes("swagger", self._docs_swagger_path),
            *self._get_doc_routes("redoc", self._docs_redoc_path),
        ]

    def _get_doc_routes(self, doc_type: str, doc_path: str) -> list[RouteDef]:
        """Add routes and file for documentation endpoints."""
        routes = []
        html_filename = f"{doc_type}.html"
        assert self._static_files_root
        static_files_root = self._static_files_root
        copy_and_patch_html(
            Path(__file__).parent / f"openapi/{html_filename}",
            self._static_files_root / f"openapi/{html_filename}",
            self._static_endpoint_prefix,
        )

        async def docs_response(_) -> aiohttp.web.FileResponse:
            return aiohttp.web.FileResponse(
                static_files_root / f"openapi/{html_filename}"
            )

        async def default_docs_redirect(
            _,
        ) -> aiohttp.web.HTTPTemporaryRedirect:
            return aiohttp.web.HTTPTemporaryRedirect(location=doc_path)

        routes.append(aiohttp.web.get(doc_path, docs_response))
        if self._docs_default_type == doc_type:
            for docs_default_path in (
                self._docs_default_path.rstrip("/"),
                f"{self._docs_default_path.rstrip('/')}/",
            ):
                routes.append(
                    aiohttp.web.get(docs_default_path, default_docs_redirect)
                )
        return routes

    async def _setup_di(self, app):
        """Set up DI integration for the app."""
        self._app_ready.set()
        setup_dishka(
            await self.context["dishka_container"],
            app,
            auto_inject=True,
            finalize_container=False,
        )


# Lightweight service to plug YAML-based config into DI (opt-in)
class AIOHTTPConfigurationService(Service):
    async def start(self) -> Any:
        pass

    async def get_di_providers(self) -> Sequence[dishka.Provider]:
        return [AIOHTTPServiceConfigProvider()]
