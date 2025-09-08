from abc import ABC
from typing import Sequence

import aiomisc
import dishka


class Service(aiomisc.Service, ABC):
    async def get_di_providers(self) -> Sequence[dishka.Provider]:
        return []
