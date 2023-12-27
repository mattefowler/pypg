from typing import Any, Callable, Collection, Iterable

from pypg import PropertyClass, Trait


class MemberNamed(Trait):
    def __init__(self, name_attr="name"):
        super().__init__()
        self.name_attr = name_attr

    def __init_instance__(self, instance: PropertyClass, named: Any):
        if named is not None and not getattr(named, self.name_attr, None):
            setattr(named, self.name_attr, self.subject.name)


def affix_index(basename, items):
    return [f"{basename} {i}" for i, item in enumerate(items)]


class MemberNameElements(MemberNamed):
    def __init__(
        self,
        name_attr="name",
        element_names_provider: Callable[
            [str, Collection], Iterable[str]
        ] = affix_index,
    ):
        super().__init__(name_attr)
        self.element_names_provider = element_names_provider

    def __init_instance__(self, instance: PropertyClass, items: Collection):
        if items is not None:
            for item, name in zip(
                items, self.element_names_provider(self.subject.name, items)
            ):
                setattr(item, self.name_attr, name)

