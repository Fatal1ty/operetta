from typing import Any, Mapping

from dishka import Provider, Scope, provide
from mashumaro.codecs.basic import decode as basic_decode

from operetta.types import ApplicationDictConfig

from .config import PrometheusServiceConfig


class PrometheusServiceConfigProvider(Provider):
    scope = Scope.APP

    def get_section(
        self, app_dict_config: ApplicationDictConfig
    ) -> Mapping[str, Any]:
        return app_dict_config.get("prometheus", {})

    @provide
    def get_config(
        self, app_dict_config: ApplicationDictConfig
    ) -> PrometheusServiceConfig:
        return basic_decode(
            self.get_section(app_dict_config), PrometheusServiceConfig
        )
