from typing import Iterable, get_origin


def hierarchy(t: type) -> Iterable[type]:
    if t.__bases__:
        for bt in t.__bases__:
            yield from hierarchy(bt)
        yield from t.__bases__


def unbind_generics(*types: type) -> Iterable[type]:
    for t in types:
        yield get_origin(t) or t


def find_closest_relative(t: type, *others: type) -> type | None:
    t, *others = unbind_generics(t, *others)
    relatives = (other for other in others if issubclass(t, other))
    try:
        return max(relatives, key=lambda other: len([*hierarchy(other)]))
    except ValueError:
        return None


def get_fully_qualified_name(t: type) -> str:
    if t.__module__ == "builtins":
        return t.__qualname__
    return ".".join((t.__module__, t.__qualname__))
