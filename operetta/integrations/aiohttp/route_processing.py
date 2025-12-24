import re
from dataclasses import dataclass
from inspect import Signature, signature
from json import JSONDecodeError
from typing import Any, Callable, get_type_hints

import aiohttp
import attr
from aiohttp.web_routedef import RouteDef
from mashumaro.codecs import BasicDecoder
from mashumaro.codecs.json import JSONEncoder
from mashumaro.codecs.orjson import ORJSONDecoder
from mashumaro.core.meta.helpers import (
    get_args,
    get_type_annotations,
    is_annotated,
    is_optional,
    not_none_type_arg,
    type_name,
)
from mashumaro.exceptions import (
    InvalidFieldValue,
    MissingDiscriminatorError,
    MissingField,
    SuitableVariantNotFoundError,
)
from openapify import (
    Body,
    PathParam,
    QueryParam,
    request_schema,
    response_schema,
)
from openapify.core.models import TypeAnnotation

from operetta.integrations.aiohttp.annotations import (
    FromBody,
    FromPath,
    FromQuery,
)
from operetta.integrations.aiohttp.errors import (
    InvalidJSONBodyError,
    InvalidPathParamsError,
    InvalidQueryParamsError,
    MissingRequiredQueryParamsError,
)
from operetta.integrations.aiohttp.request import (
    collect_exception_chain_metadata,
)
from operetta.integrations.aiohttp.response import SuccessResponse


@dataclass(kw_only=True)
class RequestHandlerParamInfo:
    handler_param_name: str


@dataclass
class RequestHandlerBodyInfo(RequestHandlerParamInfo):
    spec: Body


@dataclass
class RequestHandlerQueryParamInfo(RequestHandlerParamInfo):
    request_param_name: str
    spec: QueryParam


@dataclass
class RequestHandlerPathParamInfo(RequestHandlerParamInfo):
    request_param_name: str
    spec: PathParam


def process_route(route: RouteDef) -> RouteDef:
    body_info: RequestHandlerBodyInfo | None = None
    query_params_info: list[RequestHandlerQueryParamInfo] = []
    path_params_info: list[RequestHandlerPathParamInfo] = []

    removed_params: set[str] = set()
    injected_async_param_getters = {}
    injected_sync_param_getters = {}

    orig_func_signature = signature(route.handler)

    for func_arg in orig_func_signature.parameters.values():
        if is_annotated(func_arg.annotation):
            func_arg_annotations = get_type_annotations(func_arg.annotation)
            for func_arg_annotation in func_arg_annotations:
                if isinstance(func_arg_annotation, FromBody):  # type: ignore
                    from_body = func_arg_annotation
                    body_info = RequestHandlerBodyInfo(
                        handler_param_name=func_arg.name,
                        spec=Body(
                            value_type=get_args(func_arg.annotation)[0],
                            media_type=from_body.media_type,
                            required=from_body.required,
                            description=from_body.description,
                            example=from_body.example,
                            examples=from_body.examples,
                        ),
                    )
                elif isinstance(func_arg_annotation, FromQuery):  # type: ignore
                    from_query = func_arg_annotation
                    spec = QueryParam(
                        default=from_query.query_param.default,
                        value_type=get_args(func_arg.annotation)[0],
                        description=from_query.query_param.description,
                        deprecated=from_query.query_param.deprecated,
                        allowEmptyValue=from_query.query_param.allowEmptyValue,
                        style=from_query.query_param.style,
                        explode=from_query.query_param.explode,
                        example=from_query.query_param.example,
                        examples=from_query.query_param.examples,
                    )
                    if spec.default is None and spec.required is None:
                        if (default := func_arg.default) is Signature.empty:
                            spec.required = True
                        else:
                            spec.default = default
                    query_params_info.append(
                        RequestHandlerQueryParamInfo(
                            handler_param_name=func_arg.name,
                            request_param_name=(
                                from_query.name or func_arg.name
                            ),
                            spec=spec,
                        )
                    )
                elif isinstance(func_arg_annotation, FromPath):  # type: ignore
                    from_path = func_arg_annotation
                    spec = PathParam(  # type: ignore[assignment]
                        value_type=get_args(func_arg.annotation)[0],
                        description=from_path.description,
                        example=from_path.example,
                        examples=from_path.examples,
                    )
                    if from_path.name:
                        request_param_name = from_path.name
                    else:
                        path_param_names = re.findall(r"{([^}]+)}", route.path)
                        if len(path_param_names) == 1:
                            request_param_name = path_param_names[0]
                        else:
                            request_param_name = func_arg.name
                    path_params_info.append(
                        RequestHandlerPathParamInfo(
                            handler_param_name=func_arg.name,
                            request_param_name=request_param_name,
                            spec=spec,  # type: ignore[arg-type]
                        )
                    )
    if body_info:
        removed_params.add(body_info.handler_param_name)
        injected_async_param_getters[body_info.handler_param_name] = (
            create_body_getter(body_info.spec.value_type)
        )
    for query_param_info in query_params_info:
        removed_params.add(query_param_info.handler_param_name)
        injected_sync_param_getters[query_param_info.handler_param_name] = (
            create_query_param_getter(query_param_info)
        )

    for path_param_info in path_params_info:
        removed_params.add(path_param_info.handler_param_name)
        injected_sync_param_getters[path_param_info.handler_param_name] = (
            create_path_param_getter(path_param_info)
        )

    return_annotation = orig_func_signature.return_annotation
    response_body_encoder = get_response_body_encoder(return_annotation)

    if (
        injected_async_param_getters
        or injected_sync_param_getters
        or response_body_encoder
    ):
        orig_f = route.handler

        if response_body_encoder:

            async def wrapper(request: aiohttp.web.Request, *args, **kwargs):
                for name, getter in injected_sync_param_getters.items():
                    kwargs[name] = getter(request)
                for name, getter in injected_async_param_getters.items():
                    kwargs[name] = await getter(request)
                data = await orig_f(request, *args, **kwargs)
                return aiohttp.web.Response(
                    body=response_body_encoder(SuccessResponse(data=data)),
                    content_type="application/json",
                )

        else:

            async def wrapper(request: aiohttp.web.Request, *args, **kwargs):
                for name, getter in injected_sync_param_getters.items():
                    kwargs[name] = getter(request)
                for name, getter in injected_async_param_getters.items():
                    kwargs[name] = await getter(request)
                return await orig_f(request, *args, **kwargs)

        _preserve_handler_metadata(wrapper, orig_f, removed_params)
        _apply_openapi_schema(
            wrapper=wrapper,
            query_params_info=query_params_info,
            path_params_info=path_params_info,
            body_info=body_info,
            return_annotation=return_annotation,
        )
        route = attr.evolve(route, handler=wrapper)
    return route


def _preserve_handler_metadata(
    wrapper: Callable[[aiohttp.web.Request], Any],
    orig_f: Callable[[aiohttp.web.Request], Any],
    removed_param_names: set[str],
):
    orig_signature = signature(orig_f)

    wrapper.__name__ = orig_f.__name__
    wrapper.__qualname__ = orig_f.__qualname__
    wrapper.__doc__ = orig_f.__doc__
    wrapper.__module__ = orig_f.__module__

    wrapper.__annotations__ = {
        name: ann
        for name, ann in get_type_hints(orig_f, include_extras=True).items()
        if name not in removed_param_names
    }
    new_params = [
        param
        for name, param in orig_signature.parameters.items()
        if name not in removed_param_names
    ]
    wrapper.__signature__ = Signature(  # type: ignore[attr-defined]
        parameters=new_params,
        return_annotation=orig_signature.return_annotation,
    )
    if hasattr(orig_f, "__openapify__"):
        wrapper.__openapify__ = getattr(  # type: ignore[attr-defined]
            orig_f, "__openapify__"
        )


def _apply_openapi_schema(
    wrapper: Callable[[aiohttp.web.Request], Any],
    path_params_info: list[RequestHandlerPathParamInfo],
    query_params_info: list[RequestHandlerQueryParamInfo],
    body_info: RequestHandlerBodyInfo | None,
    return_annotation: TypeAnnotation,
):
    for param_info in path_params_info:  # type: ignore[assignment]
        request_schema(
            path_params={param_info.request_param_name: param_info.spec}
        )(wrapper)
    for param_info in query_params_info:  # type: ignore[assignment]
        if is_optional(param_info.spec.value_type):
            param_info.spec.value_type = not_none_type_arg(
                get_args(param_info.spec.value_type)
            )
        request_schema(
            query_params={param_info.request_param_name: param_info.spec}
        )(wrapper)

    if body_info:
        request_schema(body=body_info.spec)(wrapper)

    if is_response_body_annotation(return_annotation):
        response_schema(SuccessResponse[return_annotation])(wrapper)


def is_response_body_annotation(response_annotation) -> bool:
    if response_annotation is Signature.empty:
        return False
    try:
        if issubclass(response_annotation, aiohttp.web.StreamResponse):
            return False
    except TypeError:
        return True
    else:
        return True


def get_response_body_encoder(
    response_annotation,
) -> Callable[[Any], str | bytes] | None:
    if is_response_body_annotation(response_annotation):
        return JSONEncoder(SuccessResponse[response_annotation]).encode
    else:
        return None


def create_body_getter(
    value_type: TypeAnnotation,
) -> Callable[[aiohttp.web.Request], Any]:
    decoder = ORJSONDecoder(value_type).decode

    async def getter(request: aiohttp.web.Request):
        try:
            return decoder(await request.read())
        except JSONDecodeError as e:
            raise InvalidJSONBodyError(e)
        except (
            InvalidFieldValue,
            MissingField,
            MissingDiscriminatorError,
            SuitableVariantNotFoundError,
        ) as e:
            details = collect_exception_chain_metadata(e)
            raise InvalidJSONBodyError(details=details)

    return getter


def create_query_param_getter(
    param_info: RequestHandlerQueryParamInfo,
) -> Callable[[aiohttp.web.Request], Any]:
    decoder = BasicDecoder(param_info.spec.value_type).decode
    param_name = param_info.request_param_name
    required = param_info.spec.required
    param_default = param_info.spec.default
    missing_error = MissingRequiredQueryParamsError(
        details=[
            {
                "param_name": param_info.request_param_name,
                "expected_type": type_name(
                    param_info.spec.value_type, short=True
                ),
                "issue": f"Missing required query parameter '{param_name}'",
                "suggestion": (
                    "Ensure all required query parameters are provided"
                ),
            }
        ]
    )

    def getter(request: aiohttp.web.Request):
        try:
            param_value = request.query[param_name]
        except KeyError:
            if required:
                raise missing_error
            else:
                return param_default
        try:
            return decoder(param_value)
        except ValueError:
            raise InvalidQueryParamsError(
                details=[f"Invalid {param_name} format"]
            )

    return getter


def create_path_param_getter(
    param_info: RequestHandlerPathParamInfo,
) -> Callable[[aiohttp.web.Request], Any]:
    decoder = BasicDecoder(param_info.spec.value_type).decode
    request_param_name = param_info.request_param_name

    def getter(request: aiohttp.web.Request):
        value = request.match_info[request_param_name]
        try:
            return decoder(value)
        except ValueError:
            raise InvalidPathParamsError(
                details=[f"Invalid {request_param_name} format"]
            )

    return getter
