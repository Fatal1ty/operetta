import argparse
import sys
from collections.abc import Mapping
from functools import cached_property
from pathlib import Path
from typing import Any, Callable, Sequence

import aiomisc
import dishka
import yaml

from operetta.service.base import Service
from operetta.types import ApplicationDictConfig


class YAMLConfigurationService(Service):
    config_dict: ApplicationDictConfig
    config: Any
    args: argparse.Namespace

    def __init__(
        self,
        config_cls: type[Any] = ApplicationDictConfig,
        config_factory: Callable[[Mapping[str, Any]], Any] = lambda c: c,
        **kwargs,
    ) -> None:
        self.config_cls = config_cls
        self.config_factory = config_factory
        self.args = self.argument_parser.parse_args()
        if not self.args.config.is_file():
            sys.exit(
                f"Error: Configuration file '{self.args.config}' "
                f"does not exist or is not a file."
            )
        with self.args.config.open("r", encoding="utf-8") as f:
            self.config_dict = yaml.safe_load(f)
            self.config = self.config_factory(self.config_dict)
        self.setup_logging()
        super().__init__(**kwargs)

    @cached_property
    def argument_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()  # TODO: add description
        parser.add_argument(
            "-c",
            "--config",
            type=Path,
            required=True,
            help="Path to the configuration file",
        )
        parser.add_argument(
            "--log-level",
            type=str,
            default="debug",
            help="Logging level",
        )
        return parser

    def setup_logging(self) -> None:
        # TODO: why not working?
        log_level = self.config_dict.get("logging", {}).get(
            "level", self.args.log_level
        )
        aiomisc.log.basic_config(log_level)

    async def start(self) -> Any:
        pass

    async def get_di_providers(self) -> Sequence[dishka.Provider]:
        providers = []
        dict_config_provider = dishka.Provider(scope=dishka.Scope.APP)
        dict_config_provider.provide(
            lambda: self.config_dict, provides=ApplicationDictConfig
        )
        providers.append(dict_config_provider)
        if self.config_cls is not ApplicationDictConfig:
            config_provider = dishka.Provider(scope=dishka.Scope.APP)
            config_provider.provide(
                lambda: self.config, provides=self.config_cls
            )
            providers.append(config_provider)
        return providers
