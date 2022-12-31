from pypg import FunctionReference, Property
from pypg.traits import Overridable


class Obligate(Overridable, override_target="raise_error"):
    def __init__(self):
        super().__init__()

    def _override(self, *args, **kwargs):
        pass

    def __bind__(self, subject: Property):
        super().__bind__(subject)
        self.subject._default = FunctionReference(self.require_value)

    def require_value(self, *_, **__):
        self.raise_error(*_, **__)

    def raise_error(self, *_, **__):
        raise ValueError(
            f"Value for {self.subject} must be provided at initialization"
        )
