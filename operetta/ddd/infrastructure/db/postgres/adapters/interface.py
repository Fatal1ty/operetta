from abc import ABC, abstractmethod
from typing import Any


class PostgresDatabaseAdapter(ABC):
    @abstractmethod
    async def fetch(self, query: Any, *args, **kwargs) -> list[Any]:
        pass

    @abstractmethod
    async def fetch_one(self, query: Any, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    async def fetch_val(self, query: Any, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    async def fetch_one_write(self, query: Any, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    async def execute(self, query: str, *args, **kwargs) -> Any:
        pass


class PostgresTransactionDatabaseAdapter(PostgresDatabaseAdapter):
    @abstractmethod
    async def start_transaction(self) -> Any:
        pass

    @abstractmethod
    async def commit_transaction(self) -> Any:
        pass

    @abstractmethod
    async def rollback_transaction(self) -> Any:
        pass
