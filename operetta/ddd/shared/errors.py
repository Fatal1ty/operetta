from typing import Any, Sequence


class AppBaseException(Exception):
    details: Sequence[Any] = ()

    def __init__(self, *args, details: Sequence[Any] = ()):
        super().__init__(*args)
        self.details = details or self.details
