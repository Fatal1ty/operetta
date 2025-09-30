from abc import ABC
from typing import Sequence

import aiomisc
import dishka


class Service(aiomisc.Service, ABC):
    async def get_di_providers(self) -> Sequence[dishka.Provider]:
        return []

    async def get_dependency[T](self, dependency_type: type[T]) -> T:
        container: dishka.Container = await self.context["dishka_container"]
        return await container.get(dependency_type)
