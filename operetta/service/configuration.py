from pathlib import Path
from typing import Any

import aiomisc
import yaml


class ConfigurationService(aiomisc.Service):
    def __init__(self, config_path: Path, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config_path = config_path

    async def start(self) -> Any:
        with self.config_path.open("r", encoding="utf-8") as f:
            self.context["config"] = yaml.safe_load(f)
