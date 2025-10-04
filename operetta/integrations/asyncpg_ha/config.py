from dataclasses import dataclass
from enum import StrEnum

from hasql import base as hasql_base


class BalancerPolicyType(StrEnum):
    GREEDY = "greedy"
    ROUND_ROBIN = "round_robin"
    RANDOM_WEIGHTED = "random_weighted"


@dataclass
class AsyncpgHAPostgresDatabaseConfig:
    user: str
    database: str
    hosts: list[str]
    password: str | None = None
    min_masters: int | None = None
    min_replicas: int | None = None
    acquire_timeout: float | int = hasql_base.DEFAULT_ACQUIRE_TIMEOUT
    refresh_delay: float | int = hasql_base.DEFAULT_REFRESH_DELAY
    refresh_timeout: float | int = hasql_base.DEFAULT_REFRESH_TIMEOUT
    fallback_master: bool = False
    master_as_replica_weight: float = (
        hasql_base.DEFAULT_MASTER_AS_REPLICA_WEIGHT
    )
    balancer_policy: BalancerPolicyType = BalancerPolicyType.GREEDY
    stopwatch_window_size: int = hasql_base.DEFAULT_STOPWATCH_WINDOW_SIZE

    def build_dsn(self) -> str:
        hosts = ",".join(self.hosts)
        if self.password:
            creds = f"{self.user}:{self.password}"
        else:
            creds = self.user
        return f"postgresql://{creds}@{hosts}/{self.database}"
