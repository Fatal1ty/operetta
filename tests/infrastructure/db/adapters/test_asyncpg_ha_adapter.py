import pytest

from operetta.ddd.infrastructure.db.postgres.adapters.asyncpg_ha import (
    AsyncpgHAPostgresDatabaseAdapter,
)


class _FakeConn:
    def __init__(self):
        self.calls = []

    async def fetch(self, query, *args, **kwargs):
        self.calls.append(("fetch", query, args))
        return [
            {"id": 1},
        ]

    async def fetchrow(self, query, *args, **kwargs):
        self.calls.append(("fetchrow", query, args))
        return {"id": 1}

    async def fetchval(self, query, *args, **kwargs):
        self.calls.append(("fetchval", query, args))
        return 42

    async def execute(self, query, *args, **kwargs):
        self.calls.append(("execute", query, args))
        return "EXECUTE 1"


class _AcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePoolManager:
    def __init__(self, conn: _FakeConn):
        self._conn = conn
        self.acquire_replica_calls = 0
        self.acquire_master_calls = 0

    def acquire_replica(self):
        self.acquire_replica_calls += 1
        return _AcquireCtx(self._conn)

    def acquire_master(self):
        self.acquire_master_calls += 1
        return _AcquireCtx(self._conn)


@pytest.mark.asyncio
async def test_asyncpg_ha_adapter_routes_reads_to_replica_and_writes_to_master():
    conn = _FakeConn()
    pool = _FakePoolManager(conn)

    adapter = AsyncpgHAPostgresDatabaseAdapter(pool)  # type: ignore[arg-type]

    rows = await adapter.fetch("SELECT 1")
    row = await adapter.fetch_one("SELECT 2")
    write_row = await adapter.fetch_one_write("INSERT ... RETURNING id")
    exec_res = await adapter.execute("SELECT 1")

    assert rows == [{"id": 1}]
    assert row == {"id": 1}
    assert write_row == {"id": 1}
    assert exec_res == "EXECUTE 1"

    # Verify reads go to replica and writes go to master
    assert pool.acquire_replica_calls == 2
    assert pool.acquire_master_calls == 2

    # And the corresponding connection methods were called
    assert ("fetch", "SELECT 1", ()) in conn.calls
    assert ("fetchrow", "SELECT 2", ()) in conn.calls
    assert ("fetchrow", "INSERT ... RETURNING id", ()) in conn.calls
    assert ("execute", "SELECT 1", ()) in conn.calls


@pytest.mark.asyncio
async def test_asyncpg_ha_adapter_fetch_val_routes_to_replica():
    conn = _FakeConn()
    pool = _FakePoolManager(conn)

    adapter = AsyncpgHAPostgresDatabaseAdapter(pool)  # type: ignore[arg-type]

    val = await adapter.fetch_val("SELECT 42")

    assert val == 42
    assert pool.acquire_replica_calls == 1
    assert pool.acquire_master_calls == 0
    assert ("fetchval", "SELECT 42", ()) in conn.calls
