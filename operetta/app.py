from typing import Iterable

import aiomisc
from aiomisc_log import LogLevel
from dishka.provider import BaseProvider

from operetta.service.di import DIService


class Application:
    def __init__(
        self,
        *services: aiomisc.Service,
        di_providers: Iterable[BaseProvider] = (),
        description: str | None = None,
        warmup_dependencies: bool = False,
        log_level: int | str = LogLevel.debug,
        # TODO: add parameters passed to aiomisc.entrypoint
    ) -> None:
        self.app_description = description
        self.services = list(services)
        self._di_providers = list(di_providers)
        self._warmup_dependencies = warmup_dependencies
        self._log_level = log_level

    def run(self):
        services = [
            DIService(
                *self._di_providers,
                app_services=self.services,
                warmup=self._warmup_dependencies,
            ),
        ] + self.services
        loop = aiomisc.new_event_loop()
        with aiomisc.entrypoint(
            loop=loop, log_level=self._log_level, *services
        ) as loop:
            loop.run_forever()
