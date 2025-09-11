import logging
from typing import Awaitable, Callable

from aiohttp import web
from aiohttp.web_exceptions import HTTPException

from operetta.ddd.application.errors import RelatedEntityNotFoundError
from operetta.ddd.domain.errors import (
    ConflictError,
    EntityExistsError,
    EntityNotFoundError,
    ValidationError,
)
from operetta.integrations.aiohttp import errors as http_errors
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
    except http_errors.APIError as e:
        return error_response(
            message=e.message, status=e.status, code=e.code, details=e.details
        )
    except Exception as e:
        log.exception(e)
        return error_response(
            "Something went wrong",
            status=500,
            code="INTERNAL_SERVER_ERROR",
            details=[{"suggestion": "Contact support if the issue persists"}],
        )


@web.middleware
async def ddd_errors_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    try:
        resp = await handler(request)
        return resp
    except EntityExistsError as e:
        raise http_errors.DuplicateRequestError(details=e.details)
    except EntityNotFoundError as e:
        raise http_errors.ResourceNotFoundError(details=e.details)
    except RelatedEntityNotFoundError as e:
        raise http_errors.UnprocessableEntityError(details=e.details)
    except ConflictError as e:
        raise http_errors.ConflictError(details=e.details)
    except ValidationError as e:
        raise http_errors.UnprocessableEntityError(details=e.details)
