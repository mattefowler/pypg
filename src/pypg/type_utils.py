import importlib
import inspect
import pkgutil
from types import FunctionType, MethodType, ModuleType
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


def get_fully_qualified_name(t: type | FunctionType | MethodType) -> str:
    if t.__module__ == "builtins":
        return t.__qualname__
    return ".".join((t.__module__, t.__qualname__))


def get_submodules(*modules: ModuleType) -> Iterable[ModuleType]:
    for module in modules:
        for m_info in pkgutil.iter_modules(module.__spec__.submodule_search_locations):
            fqn = ".".join((module.__name__, m_info.name))
            if m_info.ispkg:
                yield from get_submodules(importlib.import_module(fqn))
            yield importlib.import_module(fqn)


def find_types(cls: type | tuple[type], *modules: ModuleType) -> Iterable[type]:
    for m in get_submodules(*modules):
        for name, obj in inspect.getmembers(m):
            if inspect.isclass(obj) and issubclass(obj, cls):
                yield obj
