import logging
from typing import Any, Sequence

import aiomisc
from dishka import Scope, ValidationSettings, make_async_container
from dishka.exceptions import NoContextValueError
from dishka.provider import BaseProvider

from operetta.service.base import Service

log = logging.getLogger(__name__)


class DIService(Service):
    def __init__(
        self,
        *providers: BaseProvider,
        app_services: Sequence[aiomisc.Service] = (),
        warmup: bool = False,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._providers = list(providers)
        self._app_services = app_services
        self._warmup = warmup
        self._started = False

    async def start(self) -> Any:
        providers = [
            *(await self._get_service_providers()),
            *self._providers,
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
                    try:
                        if factory.scope is Scope.APP:
                            log.debug(
                                "Trying to warp up %s in %s",
                                factory.provides.type_hint,
                                factory.scope,
                            )
                            await container.get(
                                dependency_type=factory.provides.type_hint,
                                component=provider.component,
                            )
                            log.debug(
                                "Warmed up %s in %s",
                                factory.provides.type_hint,
                                factory.scope,
                            )
                        elif factory.scope is Scope.REQUEST:
                            async with container() as request_container:
                                log.debug(
                                    "Trying to warm up %s in %s",
                                    factory.provides.type_hint,
                                    factory.scope,
                                )
                                try:
                                    await request_container.get(
                                        factory.provides.type_hint
                                    )
                                    log.debug(
                                        "Warmed up %s in %s",
                                        factory.provides.type_hint,
                                        factory.scope,
                                    )
                                except NoContextValueError:
                                    log.debug(
                                        "Skipping %s in %s",
                                        factory.provides.type_hint,
                                        factory.scope,
                                    )
                    except Exception as e:
                        log.error(
                            "Failed to warm up %s in %s: %r",
                            factory.provides.type_hint,
                            factory.scope,
                            e,
                        )
                        raise
            log.info("Dependencies warm-up finished successfully")
        self.context["dishka_container"] = container
        self._started = True

    async def stop(self, exception: Exception | None = None) -> Any:
        if self._started:
            container = await self.context["dishka_container"]
            if container:
                await container.close()

    async def _get_service_providers(self) -> list[BaseProvider]:
        providers: list[BaseProvider] = []
        for service in self._app_services:
            if isinstance(service, Service):
                providers.extend(await service.get_di_providers())
        return providers
