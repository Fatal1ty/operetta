import pytest
from aiohttp import web

from operetta.ddd.errors import StorageIntegrityError
from operetta.integrations.aiohttp.middlewares import (
    ddd_errors_middleware,
    unhandled_error_middleware,
)


@web.middleware
async def cors_like_middleware(request: web.Request, handler):
    try:
        resp = await handler(request)
    except web.HTTPException as e:
        e.headers["X-CORS"] = "1"
        raise
    else:
        resp.headers["X-CORS"] = "1"
        return resp


async def _boom(_: web.Request) -> web.StreamResponse:
    raise StorageIntegrityError(details=[{"info": "broken"}])


@pytest.mark.parametrize(
    "middlewares,expect_generic",
    [
        (
            [
                cors_like_middleware,
                unhandled_error_middleware,
                ddd_errors_middleware,
            ],
            False,
        ),
        (
            [
                unhandled_error_middleware,
                cors_like_middleware,
                ddd_errors_middleware,
            ],
            False,
        ),
        (
            [
                cors_like_middleware,
                ddd_errors_middleware,
                unhandled_error_middleware,
            ],
            True,
        ),
    ],
)
async def test_domain_error_json_and_headers(
    aiohttp_client, middlewares, expect_generic
):
    app = web.Application(middlewares=middlewares)
    app.router.add_get("/boom", _boom)

    client = await aiohttp_client(app)
    resp = await client.get("/boom")

    assert resp.status == 500
    assert resp.headers.get("X-CORS") == "1"

    payload = await resp.json()
    assert payload["success"] is False
    assert payload["data"] is None
    assert payload["error"]["code"] == "INTERNAL_SERVER_ERROR"
    if expect_generic:
        assert payload["error"]["message"] == "Something went wrong"
    else:
        assert payload["error"]["message"] != "Something went wrong"
