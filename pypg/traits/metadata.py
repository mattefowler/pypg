from pypg import Trait


class MetadataTrait(Trait):
    def __init__(self, value):
        super().__init__()
        self.value = value
