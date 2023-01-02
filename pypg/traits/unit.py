__all__ = ["Unit"]

from pypg.traits.metadata import MetadataTrait


class Unit(MetadataTrait):
    def __init__(self, label: str):
        super().__init__(label)
