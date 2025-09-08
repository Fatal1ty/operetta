import asyncio
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

import aiohttp
from aiohttp.typedefs import Middleware
from aiohttp.web import Application
from aiohttp.web_routedef import RouteDef
from aiomisc.service.aiohttp import AIOHTTPService as BaseAIOHTTPService
from dishka import AsyncContainer
from dishka.integrations.aiohttp import (
    DISHKA_CONTAINER_KEY,
    _inject_routes,
    container_middleware,
)

from operetta.integrations.aiohttp.openapi.builder import rebuild_spec
from operetta.integrations.aiohttp.route_processing import (
    process_route,
)
from operetta.service.base import Service

log = logging.getLogger(__name__)


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


class AIOHTTPService(Service, BaseAIOHTTPService):
    def __init__(
        self,
        routes: Iterable[RouteDef],
        middlewares: Iterable[Middleware] = (),
        static_endpoint_prefix: str = "/static/",
        static_files_root: Path | None = None,
        docs_default_path: str = "/docs",
        docs_swagger_path: str = "/docs/swagger",
        docs_redoc_path: str = "/docs/redoc",
        docs_title: str = "API",
        docs_servers: Sequence[str] = ("http://127.0.0.1:8080",),
        docs_default_type: Literal["swagger", "redoc", None] = "swagger",
        docs_remove_path_prefix: str | None = None,
        docs_tag_descriptions: dict[str, str] | None = None,
        docs_tag_groups: dict[str, list[str]] | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._routes = routes
        self._middlewares = middlewares
        self._docs_default_path = docs_default_path
        self._docs_swagger_path = docs_swagger_path
        self._docs_redoc_path = docs_redoc_path
        self._static_endpoint_prefix = static_endpoint_prefix
        if static_files_root is None:
            static_files_root = Path(tempfile.mkdtemp())
        self._static_files_root = static_files_root
        self._docs_title = docs_title
        self._docs_servers = docs_servers
        self._docs_default_type = docs_default_type
        self._docs_remove_path_prefix = docs_remove_path_prefix
        self._docs_tag_descriptions = docs_tag_descriptions
        self._docs_tag_groups = docs_tag_groups

        self._app_ready = asyncio.Event()

    async def create_application(self):
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
                routes=self._routes,
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
        copy_and_patch_html(
            Path(__file__).parent / f"openapi/{html_filename}",
            self._static_files_root / f"openapi/{html_filename}",
            self._static_endpoint_prefix,
        )

        async def docs_response(_) -> aiohttp.web.FileResponse:
            return aiohttp.web.FileResponse(
                self._static_files_root / f"openapi/{html_filename}"
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
            await self.context["dishka_container"], app, auto_inject=True
        )


def setup_dishka(
    container: AsyncContainer,
    app: Application,
    *,
    auto_inject: bool = False,
) -> None:
    # TODO: Remove after https://github.com/reagento/dishka/pull/532 or
    #  https://github.com/reagento/dishka/pull/532 released
    app[DISHKA_CONTAINER_KEY] = container
    app.middlewares.append(container_middleware)

    if auto_inject:
        _inject_routes(app.router)
