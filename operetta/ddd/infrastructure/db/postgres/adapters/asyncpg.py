from typing import Any

from asyncpg import Connection, Pool
from asyncpg.transaction import Transaction

from operetta.ddd.infrastructure.db.postgres.adapters.interface import (
    PostgresDatabaseAdapter,
    PostgresTransactionDatabaseAdapter,
)


class AsyncpgPostgresDatabaseAdapter(PostgresDatabaseAdapter):
    def __init__(self, pool: Pool):
        self._pool = pool

    async def fetch(self, query: Any, *args, **kwargs) -> list[Any]:
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args, **kwargs)

    async def fetch_one(self, query: Any, *args, **kwargs) -> Any:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args, **kwargs)

    async def fetch_val(self, query: Any, *args, **kwargs) -> Any:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args, **kwargs)

    async def fetch_one_write(self, query: Any, *args, **kwargs) -> Any:
        return await self.fetch_one(query, *args, **kwargs)

    async def execute(self, query: str, *args, **kwargs) -> Any:
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args, **kwargs)


class AsyncpgPostgresTxDatabaseAdapter(PostgresTransactionDatabaseAdapter):
    def __init__(self, conn: Connection):
        self._conn = conn
        self._tx: Transaction | None = None

    async def fetch(self, query: Any, *args, **kwargs) -> list[Any]:
        return await self._conn.fetch(query, *args, **kwargs)

    async def fetch_one(self, query: Any, *args, **kwargs) -> Any:
        return await self._conn.fetchrow(query, *args, **kwargs)

    async def fetch_val(self, query: Any, *args, **kwargs) -> Any:
        return await self._conn.fetchval(query, *args, **kwargs)

    async def fetch_one_write(self, query: Any, *args, **kwargs) -> Any:
        return await self.fetch_one(query, *args, **kwargs)

    async def execute(self, query: str, *args, **kwargs) -> Any:
        return await self._conn.execute(query, *args, **kwargs)

    async def start_transaction(self) -> Any:
        self._tx = self._conn.transaction()
        await self._tx.start()

    async def commit_transaction(self) -> Any:
        if self._tx is not None:
            await self._tx.commit()

    async def rollback_transaction(self) -> Any:
        if self._tx is not None:
            await self._tx.rollback()
