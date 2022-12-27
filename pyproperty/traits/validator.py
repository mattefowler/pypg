__all__ = ["Validator"]
from collections.abc import Callable
from typing import Any

from pyproperty import PreSet


class Validator(PreSet):
    def __init__(self, validator: Callable):
        super().__init__()
        self.validator = validator

    def apply(self, instance, value) -> Any:
        self.validator(instance, value)
        return value
