__all__ = ["Unit"]
from pyproperty.property import Trait


class Unit(Trait):
    def __init__(self, label: str):
        super().__init__()
        self.unit = label
