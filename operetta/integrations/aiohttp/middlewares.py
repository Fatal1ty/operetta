import logging
from typing import Awaitable, Callable

from aiohttp import web
from aiohttp.web_exceptions import HTTPException

from operetta.ddd import ValidationError
from operetta.ddd.errors import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DeadlineExceededError,
    DependencyFailureError,
    DependencyThrottledError,
    DependencyUnavailableError,
    InfrastructureError,
    InvalidOperationError,
    NotFoundError,
    PermissionDeniedError,
    RelatedResourceNotFoundError,
    StorageIntegrityError,
    SubsystemUnavailableError,
    SystemResourceLimitExceededError,
    TransportIntegrityError,
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
    except http_errors.APIError as e:
        return error_response(
            message=e.message, status=e.status, code=e.code, details=e.details
        )
    except HTTPException:
        raise
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
    except AlreadyExistsError as e:
        api_error: http_errors.APIError = http_errors.DuplicateRequestError(
            details=e.details
        )
    except NotFoundError as e:
        api_error = http_errors.ResourceNotFoundError(details=e.details)
    except (RelatedResourceNotFoundError, ValidationError) as e:
        api_error = http_errors.UnprocessableEntityError(details=e.details)
    except (ConflictError, InvalidOperationError) as e:
        api_error = http_errors.ConflictError(details=e.details)
    except AuthenticationError as e:
        api_error = http_errors.UnauthorizedError(details=e.details)
    except (AuthorizationError, PermissionDeniedError) as e:
        api_error = http_errors.ForbiddenError(details=e.details)
    except DeadlineExceededError as e:
        api_error = http_errors.GatewayTimeoutError(details=e.details)
    except (DependencyUnavailableError, SubsystemUnavailableError) as e:
        api_error = http_errors.ServiceUnavailableError(details=e.details)
    except DependencyFailureError as e:
        api_error = http_errors.BadGatewayError(details=e.details)
    except (StorageIntegrityError, TransportIntegrityError) as e:
        api_error = http_errors.ServerError(details=e.details)
    except (SystemResourceLimitExceededError, DependencyThrottledError) as e:
        api_error = http_errors.ServiceUnavailableError(details=e.details)
    except InfrastructureError as e:
        api_error = http_errors.ServerError(details=e.details)

    return error_response(
        message=api_error.message,
        status=api_error.status,
        code=api_error.code,
        details=api_error.details,
    )
