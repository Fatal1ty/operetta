from typing import Any, AsyncIterable, Mapping

import asyncpg
from dishka import Provider, Scope, provide

from operetta.ddd.infrastructure.db.postgres.adapters.asyncpg import (
    AsyncpgPostgresDatabaseAdapter,
    AsyncpgPostgresTxDatabaseAdapter,
)
from operetta.ddd.infrastructure.db.postgres.adapters.interface import (
    PostgresDatabaseAdapter,
    PostgresTransactionDatabaseAdapter,
)
from operetta.integrations.asyncpg.config import (
    AsyncpgPoolFactoryKwargs,
    AsyncpgPostgresDatabaseConfig,
)
from operetta.types import ApplicationDictConfig


class AsyncpgPostgresDatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_db_pool(
        self,
        config: AsyncpgPostgresDatabaseConfig,
        pool_factory_kwargs: AsyncpgPoolFactoryKwargs,
    ) -> AsyncIterable[asyncpg.pool.Pool]:
        async with asyncpg.create_pool(
            dsn=config.build_dsn(),
            min_size=config.min_size,
            max_size=config.max_size,
            max_queries=config.max_queries,
            max_inactive_connection_lifetime=config.max_inactive_connection_lifetime,
            init=pool_factory_kwargs.get("init"),
        ) as pool:
            yield pool

    @provide(scope=Scope.REQUEST)
    async def get_tx_connection(
        self, pool: asyncpg.Pool
    ) -> AsyncIterable[asyncpg.Connection]:
        async with pool.acquire() as conn:
            yield conn  # type: ignore

    db_adapter = provide(
        AsyncpgPostgresDatabaseAdapter,
        provides=PostgresDatabaseAdapter,
        scope=Scope.APP,
    )
    tx_db_adapter = provide(
        AsyncpgPostgresTxDatabaseAdapter,
        provides=PostgresTransactionDatabaseAdapter,
        scope=Scope.REQUEST,
    )


class AsyncpgPostgresDatabaseConfigProvider(Provider):
    scope = Scope.APP

    def get_postgres_section(
        self, app_dict_config: ApplicationDictConfig
    ) -> Mapping[str, Any]:
        if "postgres" not in app_dict_config:
            raise ValueError(
                "Missing 'postgres' section in application config"
            )
        return app_dict_config["postgres"]

    @provide
    def get_db_config(
        self, app_dict_config: ApplicationDictConfig
    ) -> AsyncpgPostgresDatabaseConfig:
        db_config = self.get_postgres_section(app_dict_config)
        db_config_kwargs = {
            "user": db_config["user"],
            "database": db_config["database"],
            "host": db_config["host"],
            "password": db_config.get("password"),
        }
        if (min_size := db_config.get("min_size")) is not None:
            db_config_kwargs["min_size"] = min_size
        if (max_size := db_config.get("max_size")) is not None:
            db_config_kwargs["max_size"] = max_size
        if (max_queries := db_config.get("max_queries")) is not None:
            db_config_kwargs["max_queries"] = max_queries
        if (
            max_inactive_connection_lifetime := db_config.get(
                "max_inactive_connection_lifetime"
            )
        ) is not None:
            db_config_kwargs["max_inactive_connection_lifetime"] = (
                max_inactive_connection_lifetime
            )

        return AsyncpgPostgresDatabaseConfig(**db_config_kwargs)

    @provide
    def get_pool_factory_kwargs(self) -> AsyncpgPoolFactoryKwargs:
        return {}
