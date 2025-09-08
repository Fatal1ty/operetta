from typing import Any, Sequence


class APIError(Exception):
    status: int = 500
    code: str | None = None
    message_format: str = ""
    details: Sequence[Any] = ()

    def __init__(self, *args, details: Sequence[str] = ()):
        super().__init__(*args)
        self.details = details

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


class InvalidPathParamsError(ClientError):
    code = "INVALID_PATH_PARAMS"
    message_format = "Invalid path parameters"


class ResourceNotFoundError(ClientError):
    status = 404
    code = "RESOURCE_NOT_FOUND"
    message_format = "Resource not found"
