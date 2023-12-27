from typing import Any

from pypg import PropertyClass, Trait


class MemberNamed(Trait):
    def __init__(self, name_attr="name"):
        super().__init__()
        self.name_attr = name_attr

    def __init_instance__(self, instance: PropertyClass, named: Any):
        if named is not None and not getattr(named, self.name_attr, None):
            setattr(named, self.name_attr, self.subject.name)
