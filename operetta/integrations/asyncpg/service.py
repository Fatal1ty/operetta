from typing import Any, Sequence

import dishka

from operetta.integrations.asyncpg.providers import (
    AsyncpgPostgresDatabaseConfigProvider,
    AsyncpgPostgresDatabaseProvider,
)
from operetta.service.base import Service


class AsyncpgPostgresDatabaseService(Service):
    async def start(self) -> Any:
        pass

    async def get_di_providers(self) -> Sequence[dishka.Provider]:
        return [AsyncpgPostgresDatabaseProvider()]


class AsyncpgPostgresDatabaseConfigurationService(Service):
    async def start(self) -> Any:
        pass

    async def get_di_providers(self) -> Sequence[dishka.Provider]:
        return [AsyncpgPostgresDatabaseConfigProvider()]
