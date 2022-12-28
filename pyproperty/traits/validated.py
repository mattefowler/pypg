__all__ = ["Validated"]

from abc import ABC
from collections.abc import Callable
from typing import Any

from pyproperty.property import DataModifierMixin
from . import Overridable


class Validated(Overridable, DataModifierMixin, ABC):
    def __init__(self, validator: Callable):
        super().__init__(self.apply)
        self.validator = validator

    def apply(self, instance, value) -> Any:
        self.validator(instance, value)
        return value

    def _override(self, instance, value):
        return value
