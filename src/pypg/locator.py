from pydoc import locate as _locate
from types import FunctionType, MethodType
from typing import Protocol

from pypg.type_utils import get_fully_qualified_name


def _disallow(name):
    raise PermissionError(f"dynamic loading of {name} not allowed")


class LoadPolicy(Protocol):
    def __call__(
        self, typedict: dict[str, type], fully_qualified_name: str
    ):  # pragma: no cover
        pass


def strict(typedict: dict[str, type], fully_qualified_name: str):
    try:
        return typedict[fully_qualified_name]
    except KeyError:
        _disallow(fully_qualified_name)


def allow_subclass(typedict: dict[str, type], fully_qualified_name: str):
    t: type = _locate(fully_qualified_name)
    if any(issubclass(t, allowed) for allowed in typedict.values()):
        return t


_special_cases = {
    get_fully_qualified_name(NoneType := type(None)): NoneType,
    get_fully_qualified_name(FunctionType): FunctionType,
    get_fully_qualified_name(MethodType): MethodType,
}


class Locator:
    def __init__(self, *allowed: type, load_policy: LoadPolicy | None = None):
        self.__load_policy = load_policy
        self.__allowed: dict[str, type] = {
            get_fully_qualified_name(allowed_type): allowed_type
            for allowed_type in allowed
        }

    def allow(self, t: type):
        self.__allowed[get_fully_qualified_name(t)] = t

    def __call__(self, fully_qualified_name: str):
        if self.__load_policy:
            return self.__load_policy(self.__allowed, fully_qualified_name)
        else:
            result = _locate(fully_qualified_name)
            if result is None:
                try:
                    return _special_cases[fully_qualified_name]
                except KeyError:
                    raise TypeError(f"unable to locate {fully_qualified_name}")
            return result
