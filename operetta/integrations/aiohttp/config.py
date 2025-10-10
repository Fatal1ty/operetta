from dataclasses import dataclass
from typing import Literal, Sequence


@dataclass
class AIOHTTPServiceConfig:
    """Configuration for AIOHTTPService.

    Only runtime/server and documentation-related settings live here.
    Routes and middlewares are configured in code.
    """

    address: str = "localhost"
    port: int = 8080

    static_endpoint_prefix: str = "/static/"
    static_files_root: str | None = None

    docs_default_path: str = "/docs"
    docs_swagger_path: str = "/docs/swagger"
    docs_redoc_path: str = "/docs/redoc"
    docs_title: str = "API"
    docs_servers: Sequence[str] = ("http://127.0.0.1:8080",)
    docs_default_type: Literal["swagger", "redoc", None] = "swagger"
    docs_remove_path_prefix: str | None = None
    docs_tag_descriptions: dict[str, str] | None = None
    docs_tag_groups: dict[str, list[str]] | None = None
