import logging
from typing import Awaitable, Callable

from aiohttp import web
from aiohttp.web_exceptions import HTTPException

from operetta.integrations.aiohttp.errors import APIError
from operetta.integrations.aiohttp.response import error_response

log = logging.getLogger(__name__)


@web.middleware
async def unhandled_error_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    try:
        resp = await handler(request)
        return resp
    except HTTPException:
        raise
    except APIError as e:
        return error_response(
            message=e.message, status=e.status, code=e.code, details=e.details
        )
    except Exception as e:
        log.exception(e)
        return error_response(
            "Something went wrong", status=500, code="INTERNAL_SERVER_ERROR"
        )
