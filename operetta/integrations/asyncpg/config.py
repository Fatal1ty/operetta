from dataclasses import dataclass
from typing import Any, Callable, Coroutine

import asyncpg
from typing_extensions import TypedDict


@dataclass
class AsyncpgPoolFactoryKwargs(TypedDict, total=False):
    init: Callable[[asyncpg.Connection], Coroutine[Any, Any, Any]] | None


@dataclass
class AsyncpgPostgresDatabaseConfig:
    user: str
    database: str
    host: str
    password: str | None = None
    min_size: int = 10
    max_size: int = 10
    max_queries: int = 50000
    max_inactive_connection_lifetime: float = 300.0

    def build_dsn(self) -> str:
        if self.password:
            creds = f"{self.user}:{self.password}"
        else:
            creds = self.user
        return f"postgresql://{creds}@{self.host}/{self.database}"
