import logging
from functools import partial
from pathlib import Path
from typing import Iterable, Sequence, Union

from apispec.yaml_utils import dict_to_yaml
from openapify.core.const import (
    DEFAULT_OPENAPI_VERSION,
    DEFAULT_SPEC_TITLE,
    DEFAULT_SPEC_VERSION,
)
from openapify.core.models import RouteDef
from openapify.ext.web.aiohttp import AioHttpRouteDef, build_spec

logger = logging.getLogger(__name__)


def route_postprocessor(
    route: RouteDef, remove_prefix: str | None = None
) -> RouteDef | None:
    if remove_prefix and route.path.startswith(remove_prefix):
        route.path = route.path[len(remove_prefix) :] or "/"
    return route


def rebuild_spec(
    routes: Iterable[AioHttpRouteDef],
    spec_path: Union[str, Path],
    title: str = DEFAULT_SPEC_TITLE,
    servers: Sequence[str] = ("http://127.0.0.1:8080",),
    tag_descriptions: dict[str, str] | None = None,
    tag_groups: dict[str, list[str]] | None = None,
    remove_path_prefix: str | None = None,
) -> None:
    if remove_path_prefix:
        remove_path_prefix = remove_path_prefix.rstrip("/")
    spec = build_spec(  # type: ignore[assignment]
        routes,
        title=title,
        version=DEFAULT_SPEC_VERSION,
        openapi_version=DEFAULT_OPENAPI_VERSION,
        servers=list(servers),
        route_postprocessor=partial(
            route_postprocessor, remove_prefix=remove_path_prefix
        ),
    )

    spec_dict = spec.to_dict()

    if tag_descriptions:
        spec_dict["tags"] = [
            {"name": tag_name, "description": tag_description}
            for tag_name, tag_description in tag_descriptions.items()
        ]
    if tag_groups:
        spec_dict["x-tagGroups"] = [
            {"name": group_name, "tags": group_tags}
            for group_name, group_tags in tag_groups.items()
        ]

    with open(spec_path, "w") as f:
        f.write(
            dict_to_yaml(spec_dict, yaml_dump_kwargs={"allow_unicode": True})
        )
