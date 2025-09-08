import argparse
import sys
from pathlib import Path
from typing import Iterable

import aiomisc
from aiomisc import get_context
from dishka.provider import BaseProvider

from operetta.service.configuration import ConfigurationService
from operetta.service.di import DIService


class Application:

    def __init__(
        self,
        *services: aiomisc.Service,
        di_providers: Iterable[BaseProvider],
        description: str | None = None,
        warmup_dependencies: bool = False,
    ):
        self.app_description = description
        self.services = list(services)
        self._di_providers = list(di_providers)
        self._warmup_dependencies = warmup_dependencies

    def run(self):
        parser = argparse.ArgumentParser(description=self.app_description)
        parser.add_argument(
            "-c",
            "--config",
            type=Path,
            required=True,
            help="Path to the configuration file.",
        )

        args = parser.parse_args()

        if not args.config.is_file():
            sys.exit(
                f"Error: Configuration file '{args.config}' does not exist "
                f"or is not a file."
            )

        async def start_services():
            entrypoint = aiomisc.entrypoint.get_current()
            services = [
                ConfigurationService(args.config),
                DIService(
                    *self._di_providers,
                    warmup=self._warmup_dependencies,
                ),
            ] + self.services
            get_context()["app"] = self
            await entrypoint.start_services(*services)

        with aiomisc.entrypoint() as loop:
            loop.create_task(start_services())
            loop.run_forever()
