import pytest

from operetta.ddd.infrastructure.db.postgres.adapters.asyncpg import (
    AsyncpgPostgresDatabaseAdapter,
    AsyncpgPostgresTxDatabaseAdapter,
)


class _FakeConn:
    def __init__(self):
        self.calls = []
        self._tx = _FakeTx()

    async def fetch(self, query, *args, **kwargs):
        self.calls.append(("fetch", query, args))
        return [
            {"id": 1},
        ]

    async def fetchrow(self, query, *args, **kwargs):
        self.calls.append(("fetchrow", query, args))
        return {"id": 1}

    async def execute(self, query, *args, **kwargs):
        self.calls.append(("execute", query, args))
        return "EXECUTE 1"

    def transaction(self):
        return self._tx


class _AcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self._conn = conn
        self.acquire_calls = 0

    def acquire(self):
        self.acquire_calls += 1
        return _AcquireCtx(self._conn)


class _FakeTx:
    def __init__(self):
        self.started = False
        self.committed = False
        self.rolled_back = False

    async def start(self):
        self.started = True

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_asyncpg_adapter_fetch_and_execute():
    conn = _FakeConn()
    pool = _FakePool(conn)
    adapter = AsyncpgPostgresDatabaseAdapter(pool)  # type: ignore[arg-type]

    rows = await adapter.fetch("SELECT 1")
    row = await adapter.fetch_one("SELECT 1")
    exec_res = await adapter.execute("SELECT 1")

    assert rows == [{"id": 1}]
    assert row == {"id": 1}
    assert exec_res == "EXECUTE 1"
    assert ("fetch", "SELECT 1", ()) in conn.calls
    assert ("fetchrow", "SELECT 1", ()) in conn.calls
    assert ("execute", "SELECT 1", ()) in conn.calls
    assert pool.acquire_calls == 3


@pytest.mark.asyncio
async def test_asyncpg_adapter_fetch_one_write_aliases_fetch_one():
    conn = _FakeConn()
    pool = _FakePool(conn)
    adapter = AsyncpgPostgresDatabaseAdapter(pool)  # type: ignore[arg-type]

    row = await adapter.fetch_one_write("INSERT ... RETURNING id")
    assert row == {"id": 1}
    assert any(call[0] == "fetchrow" for call in conn.calls)


@pytest.mark.asyncio
async def test_asyncpg_tx_adapter_tx_lifecycle_and_calls():
    conn = _FakeConn()
    adapter = AsyncpgPostgresTxDatabaseAdapter(conn)  # type: ignore[arg-type]

    await adapter.start_transaction()
    assert conn._tx.started is True

    await adapter.fetch("SELECT 1")
    await adapter.fetch_one("SELECT 2")
    await adapter.execute("SELECT 1")

    assert ("fetch", "SELECT 1", ()) in conn.calls
    assert ("fetchrow", "SELECT 2", ()) in conn.calls
    assert ("execute", "SELECT 1", ()) in conn.calls

    await adapter.commit_transaction()
    assert conn._tx.committed is True


@pytest.mark.asyncio
async def test_asyncpg_tx_adapter_commit_and_rollback_without_start_are_noops():
    conn = _FakeConn()
    adapter = AsyncpgPostgresTxDatabaseAdapter(conn)  # type: ignore[arg-type]

    assert getattr(adapter, "_tx") is None
    await adapter.commit_transaction()
    await adapter.rollback_transaction()
    assert getattr(adapter, "_tx") is None


@pytest.mark.asyncio
async def test_asyncpg_tx_adapter_fetch_one_write_aliases_fetch_one():
    conn = _FakeConn()
    adapter = AsyncpgPostgresTxDatabaseAdapter(conn)  # type: ignore[arg-type]

    row = await adapter.fetch_one_write("SELECT 1")
    assert row == {"id": 1}
    assert ("fetchrow", "SELECT 1", ()) in conn.calls


@pytest.mark.asyncio
async def test_asyncpg_tx_adapter_rollback_on_started_tx():
    conn = _FakeConn()
    adapter = AsyncpgPostgresTxDatabaseAdapter(conn)  # type: ignore[arg-type]

    await adapter.start_transaction()
    assert conn._tx.started is True

    await adapter.rollback_transaction()
    assert conn._tx.rolled_back is True
