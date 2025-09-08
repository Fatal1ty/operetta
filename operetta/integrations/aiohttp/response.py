from dataclasses import dataclass, field
from typing import Any, Generic, Mapping, Sequence, TypeVar

import aiohttp.web


def success_response(
    data: dict[str, Any] | list[Any] | None = None, status: int = 200
) -> aiohttp.web.Response:
    return aiohttp.web.json_response(
        {"success": True, "data": data, "error": None}, status=status
    )


def error_response(
    message: str,
    status: int,
    code: str | None = None,
    details: Sequence[Any] = (),
    headers: Mapping[str, str] | None = None,
) -> aiohttp.web.Response:
    response: dict[str, Any] = {
        "success": False,
        "data": None,
        "error": {"message": message, "code": code or str(status)},
    }
    if details and isinstance(details[0], str):
        details = [{"message": detail for detail in details}]
    response["error"]["details"] = details
    return aiohttp.web.json_response(response, status=status, headers=headers)


@dataclass
class ErrorSchema:
    message: str
    code: str


@dataclass
class ResponseSchema[T]:
    success: bool
    data: T
    error: ErrorSchema | None


@dataclass
class SuccessResponse[T](ResponseSchema[T]):
    success: bool = True
    data: T = field(kw_only=True)
    error: None = None
