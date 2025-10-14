from typing import Any, Mapping

from dishka import Provider, Scope, provide
from mashumaro.codecs.basic import decode as basic_decode

from operetta.types import ApplicationDictConfig

from .config import SentryServiceConfig


class SentryServiceConfigProvider(Provider):
    scope = Scope.APP

    def get_section(
        self, app_dict_config: ApplicationDictConfig
    ) -> Mapping[str, Any]:
        return app_dict_config.get("sentry", {})

    @provide
    def get_config(
        self, app_dict_config: ApplicationDictConfig
    ) -> SentryServiceConfig:
        return basic_decode(
            self.get_section(app_dict_config), SentryServiceConfig
        )
