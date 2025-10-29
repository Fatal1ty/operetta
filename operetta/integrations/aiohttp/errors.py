from typing import Any, Sequence


class APIError(Exception):
    status: int = 500
    code: str | None = None
    message_format: str = ""
    details: Sequence[Any] = ()

    def __init__(self, *args, details: Sequence[Any] = ()):
        super().__init__(*args)
        self.details = details or self.details

    @property
    def message(self) -> str:
        return self.message_format.format(*self.args)


class ClientError(APIError):
    status = 400
    code = "CLIENT_ERROR"


class ServerError(APIError):
    status = 500
    code = "INTERNAL_SERVER_ERROR"


class InvalidJSONBodyError(ClientError):
    code = "INVALID_JSON_BODY"
    message_format = "Invalid JSON body"


class InvalidQueryParamsError(ClientError):
    code = "INVALID_QUERY_PARAMS"
    message_format = "Invalid query parameters"


class MissingRequiredQueryParamsError(ClientError):
    code = "MISSING_REQUIRED_QUERY_PARAMS"
    message_format = "Missing required query parameters"
    details = [
        {"suggestion": "Ensure all required query parameters are provided"}
    ]


class InvalidPathParamsError(ClientError):
    code = "INVALID_PATH_PARAMS"
    message_format = "Invalid path parameters"


class UnauthorizedError(ClientError):
    status = 401
    code = "UNAUTHORIZED"
    message_format = "Unauthorized"


class ForbiddenError(ClientError):
    status = 403
    code = "FORBIDDEN"
    message_format = "Forbidden"


class ResourceNotFoundError(ClientError):
    status = 404
    code = "RESOURCE_NOT_FOUND"
    message_format = "Resource not found"
    details = [
        {
            "suggestion": (
                "Ensure the resource identifier is correct "
                "or the resource exists"
            )
        }
    ]


class ConflictError(ClientError):
    status = 409
    code = "CONFLICT"
    message_format = "Conflict"


class DuplicateRequestError(ConflictError):
    code = "DUPLICATE_RESOURCE"
    message_format = "Duplicate resource"
    details = [{"suggestion": "Ensure the resource does not already exist"}]


class UnprocessableEntityError(ClientError):
    status = 422
    code = "UNPROCESSABLE_ENTITY"
    message_format = "Unprocessable entity"
    details = [
        {
            "suggestion": (
                "Ensure the request data meets all required constraints"
            )
        }
    ]


class BadGatewayError(ServerError):
    status = 502
    code = "BAD_GATEWAY"
    message_format = "Bad Gateway"


class ServiceUnavailableError(ServerError):
    status = 503
    code = "SERVICE_UNAVAILABLE"
    message_format = "Service unavailable"


class GatewayTimeoutError(ServerError):
    status = 504
    code = "GATEWAY_TIMEOUT"
    message_format = "Gateway timeout"
