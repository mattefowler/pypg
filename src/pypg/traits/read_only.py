from typing import Any

from pypg import PreSet
from pypg.traits import Overridable


class ReadOnly(Overridable, PreSet, override_target="apply"):
    def __init__(self):
        super().__init__()

    def _override(self, instance, value):
        return value

    def apply(self, instance, value) -> Any:
        if self.subject.attribute_key in instance.__dict__:
            raise PermissionError(
                f"{self.subject} of {instance} is read-only and cannot be reassigned."
            )
        return value
