from abc import ABC
from typing import Generic, Sequence, TypeVar

import aiomisc
import dishka

T = TypeVar("T")


class Service(aiomisc.Service, ABC, Generic[T]):
    async def get_di_providers(self) -> Sequence[dishka.Provider]:
        return []

    async def get_dependency(self, dependency_type: type[T]) -> T:
        container: dishka.Container = await self.context["dishka_container"]
        return await container.get(dependency_type)
