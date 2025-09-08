import logging
from contextlib import suppress
from typing import Any

from dishka import Scope, ValidationSettings, make_async_container
from dishka.exceptions import NoContextValueError
from dishka.provider import BaseProvider

from operetta.service.base import Service

log = logging.getLogger(__name__)


class DIService(Service):
    def __init__(
        self, *providers: BaseProvider, warmup: bool = False, **kwargs: Any
    ):
        super().__init__(**kwargs)
        self._providers = list(providers)
        self._warmup = warmup

    async def start(self) -> Any:
        providers = [
            *self._providers,
            *(await self._get_service_providers()),
        ]
        container = make_async_container(
            *providers,
            validation_settings=ValidationSettings(
                nothing_overridden=True,
                implicit_override=True,
                nothing_decorated=True,
            ),
        )
        if self._warmup:
            log.debug("Starting dependencies warm-up...")
            for provider in providers:
                for factory in provider.factories:
                    if factory.scope is Scope.APP:
                        await container.get(factory.provides.type_hint)
                    elif factory.scope is Scope.REQUEST:
                        async with container() as request_container:
                            with suppress(NoContextValueError):
                                await request_container.get(
                                    factory.provides.type_hint
                                )
            log.info("Dependencies warm-up finished successfully")
        self.context["dishka_container"] = container

    async def stop(self, exception: Exception | None = None) -> Any:
        container = await self.context["dishka_container"]
        if container:
            await container.close()

    async def _get_service_providers(self) -> list[BaseProvider]:
        providers: list[BaseProvider] = []
        app = await self.context["app"]
        for service in app.services:
            if isinstance(service, Service):
                providers.extend(await service.get_di_providers())
        return providers
