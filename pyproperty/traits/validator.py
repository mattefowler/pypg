__all__ = ["Validator"]
from collections.abc import Callable
from typing import Any

from pyproperty import PreSet


class Validator(PreSet):
    def __init__(self, validator: Callable):
        self.validator = validator

    def apply(self, value) -> Any:
        self.validator(value)
