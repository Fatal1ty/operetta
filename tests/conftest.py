import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer
from aiohttp.web import Application


@pytest_asyncio.fixture
async def aiohttp_client():
    async def _make_client(app: Application) -> TestClient:
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        return client

    clients: list[TestClient] = []

    async def factory(app: Application) -> TestClient:
        client = await _make_client(app)
        clients.append(client)
        return client

    try:
        yield factory
    finally:
        for client in clients:
            await client.close()

