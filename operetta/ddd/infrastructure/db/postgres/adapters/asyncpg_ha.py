from typing import Any

from hasql.asyncpg import PoolManager

from operetta.ddd.infrastructure.db.postgres.adapters.asyncpg import (
    AsyncpgPostgresTxDatabaseAdapter,
)
from operetta.ddd.infrastructure.db.postgres.adapters.interface import (
    PostgresDatabaseAdapter,
)


class AsyncpgHAPostgresDatabaseAdapter(PostgresDatabaseAdapter):
    def __init__(self, pool: PoolManager):
        self._pool = pool

    async def fetch(self, query: Any, *args, **kwargs) -> list[Any]:
        async with self._pool.acquire_replica() as conn:
            return await conn.fetch(query, *args, **kwargs)

    async def fetch_one(self, query: Any, *args, **kwargs) -> Any:
        async with self._pool.acquire_replica() as conn:
            return await conn.fetchrow(query, *args, **kwargs)

    async def fetch_val(self, query: Any, *args, **kwargs) -> Any:
        async with self._pool.acquire_replica() as conn:
            return await conn.fetchval(query, *args, **kwargs)

    async def fetch_one_write(self, query: Any, *args, **kwargs) -> Any:
        async with self._pool.acquire_master() as conn:
            return await conn.fetchrow(query, *args, **kwargs)

    async def execute(self, query: str, *args, **kwargs) -> Any:
        async with self._pool.acquire_master() as conn:
            return await conn.execute(query, *args, **kwargs)


class AsyncpgHAPostgresTxDatabaseAdapter(AsyncpgPostgresTxDatabaseAdapter):
    pass
