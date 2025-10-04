import logging
from typing import Any, AsyncIterable, Mapping

import asyncpg
import hasql.asyncpg
from dishka import Provider, Scope, provide
from hasql.balancer_policy import (
    GreedyBalancerPolicy,
    RandomWeightedBalancerPolicy,
    RoundRobinBalancerPolicy,
)

from operetta.ddd.infrastructure.db.postgres.adapters.asyncpg_ha import (
    AsyncpgHAPostgresDatabaseAdapter,
    AsyncpgHAPostgresTxDatabaseAdapter,
)
from operetta.ddd.infrastructure.db.postgres.adapters.interface import (
    PostgresDatabaseAdapter,
    PostgresTransactionDatabaseAdapter,
)
from operetta.integrations.asyncpg.config import AsyncpgPoolFactoryKwargs
from operetta.integrations.asyncpg_ha.config import (
    AsyncpgHAPostgresDatabaseConfig,
    BalancerPolicyType,
)
from operetta.types import ApplicationDictConfig

log = logging.getLogger(__name__)


BALANCER_POLICY_MAP = {
    BalancerPolicyType.GREEDY: GreedyBalancerPolicy,
    BalancerPolicyType.ROUND_ROBIN: RoundRobinBalancerPolicy,
    BalancerPolicyType.RANDOM_WEIGHTED: RandomWeightedBalancerPolicy,
}


class AsyncpgHAPostgresDatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_db_pool(
        self,
        config: AsyncpgHAPostgresDatabaseConfig,
        pool_factory_kwargs: AsyncpgPoolFactoryKwargs,
    ) -> AsyncIterable[hasql.asyncpg.PoolManager]:
        pool = hasql.asyncpg.PoolManager(
            dsn=config.build_dsn(),
            acquire_timeout=config.acquire_timeout,
            refresh_delay=config.refresh_delay,
            refresh_timeout=config.refresh_timeout,
            fallback_master=config.fallback_master,
            master_as_replica_weight=config.master_as_replica_weight,
            balancer_policy=BALANCER_POLICY_MAP[config.balancer_policy],
            stopwatch_window_size=config.stopwatch_window_size,
            pool_factory_kwargs=dict(pool_factory_kwargs),
        )
        try:
            await pool.ready(
                masters_count=config.min_masters,
                replicas_count=config.min_replicas,
            )
        except Exception as e:
            log.error("Failed to get pool ready: %r", e)
            raise
        yield pool
        await pool.close()

    @provide(scope=Scope.REQUEST)
    async def get_tx_connection(
        self, pool: hasql.asyncpg.PoolManager
    ) -> AsyncIterable[asyncpg.Connection]:
        async with pool.acquire_master() as conn:
            yield conn

    db_adapter = provide(
        AsyncpgHAPostgresDatabaseAdapter,
        provides=PostgresDatabaseAdapter,
        scope=Scope.APP,
    )
    tx_db_adapter = provide(
        AsyncpgHAPostgresTxDatabaseAdapter,
        provides=PostgresTransactionDatabaseAdapter,
        scope=Scope.REQUEST,
    )


class AsyncpgHAPostgresDatabaseConfigProvider(Provider):
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
    ) -> AsyncpgHAPostgresDatabaseConfig:
        db_config = self.get_postgres_section(app_dict_config)
        db_config_kwargs = {
            "user": db_config["user"],
            "database": db_config["database"],
            "hosts": db_config["hosts"],
            "password": db_config.get("password"),
            "min_masters": db_config.get("min_masters"),
            "min_replicas": db_config.get("min_replicas"),
        }
        if (acquire_timeout := db_config.get("acquire_timeout")) is not None:
            db_config_kwargs["acquire_timeout"] = acquire_timeout
        if (refresh_delay := db_config.get("refresh_delay")) is not None:
            db_config_kwargs["refresh_delay"] = refresh_delay
        if (refresh_timeout := db_config.get("refresh_timeout")) is not None:
            db_config_kwargs["refresh_timeout"] = refresh_timeout
        if (fallback_master := db_config.get("fallback_master")) is not None:
            db_config_kwargs["fallback_master"] = fallback_master
        if (
            master_as_replica_weight := db_config.get(
                "master_as_replica_weight"
            )
        ) is not None:
            db_config_kwargs["master_as_replica_weight"] = (
                master_as_replica_weight
            )
        if (balancer_policy := db_config.get("balancer_policy")) is not None:
            db_config_kwargs["balancer_policy"] = balancer_policy
        if (
            stopwatch_window_size := db_config.get("stopwatch_window_size")
        ) is not None:
            db_config_kwargs["stopwatch_window_size"] = stopwatch_window_size
        return AsyncpgHAPostgresDatabaseConfig(**db_config_kwargs)

    @provide
    def get_pool_factory_kwargs(self) -> AsyncpgPoolFactoryKwargs:
        return {}
