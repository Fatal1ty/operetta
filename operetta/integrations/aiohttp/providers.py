from typing import Any, Mapping

from dishka import Provider, Scope, provide
from mashumaro.codecs.basic import decode as basic_decode

from operetta.types import ApplicationDictConfig

from .config import AIOHTTPServiceConfig


class AIOHTTPServiceConfigProvider(Provider):
    scope = Scope.APP

    def get_section(
        self, app_dict_config: ApplicationDictConfig
    ) -> Mapping[str, Any]:
        return app_dict_config.get("api", {})

    @provide
    def get_config(
        self, app_dict_config: ApplicationDictConfig
    ) -> AIOHTTPServiceConfig:
        return basic_decode(
            self.get_section(app_dict_config), AIOHTTPServiceConfig
        )
