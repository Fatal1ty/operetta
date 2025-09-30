from typing import Any, Sequence

import dishka

from operetta.integrations.asyncpg_ha.providers import (
    AsyncpgHAPostgresDatabaseConfigProvider,
    AsyncpgHAPostgresDatabaseProvider,
)
from operetta.service.base import Service


class AsyncpgHAPostgresDatabaseService(Service):
    async def start(self) -> Any:
        pass

    async def get_di_providers(self) -> Sequence[dishka.Provider]:
        return [AsyncpgHAPostgresDatabaseProvider()]


class AsyncpgHAPostgresDatabaseConfigurationService(Service):
    async def start(self) -> Any:
        pass

    async def get_di_providers(self) -> Sequence[dishka.Provider]:
        return [AsyncpgHAPostgresDatabaseConfigProvider()]
