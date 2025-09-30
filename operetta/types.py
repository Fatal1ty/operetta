from dataclasses import dataclass, field
from typing import NewType

ApplicationDictConfig = NewType("ApplicationDictConfig", dict)


@dataclass
class ApplicationLoggingConfig:
    level: str = "debug"
    # TODO: add more options?


@dataclass(kw_only=True)
class ApplicationDataclassConfig:
    logging: ApplicationLoggingConfig = field(
        default_factory=ApplicationLoggingConfig
    )
