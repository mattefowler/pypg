from __future__ import annotations

__all__ = ["Overridable"]

import itertools
import threading
from abc import abstractmethod
from collections import defaultdict
from collections.abc import Callable

from pypg import Property, PropertyClass, PropertyType, Trait
from pypg.type_registry import TypeRegistry

OverrideScope = PropertyType | PropertyClass | Property


def _current_thread_id():
    return threading.current_thread().native_id


class Override:
    _locks: dict[OverrideScope, tuple[threading.RLock, int]] = defaultdict(
        lambda: (threading.RLock(), 0)
    )

    def __init__(self, subject: Overridable | type[Overridable], scope: OverrideScope):
        self.subject = subject
        self._scope = scope

    def _revert(self):
        setattr(
            self.subject,
            self.subject._override_target.__name__,
            self.subject._override_target,
        )

    def _apply(self):
        setattr(
            self.subject,
            self.subject._override_target.__name__,
            self._override,
        )

    def _override(self, *args, **kwargs):
        target = (
            self.subject._override
            if self._thread_id == _current_thread_id()
            else self.subject._override_target
        )
        return target(*args, **kwargs)

    def _lock_scope(self):
        lock, count = self._locks[self._scope]
        lock.acquire()
        count += 1
        self._locks[self._scope] = (lock, count)

    def _release_scope(self):
        lock, count = self._locks[self._scope]
        count -= 1
        if not count:
            self._locks.pop(self._scope)
        else:
            self._locks[self._scope] = (lock, count)
        lock.release()

    def __enter__(self):
        self._lock_scope()
        self._thread_id = _current_thread_id()
        self._apply()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._thread_id = None
        self._revert()
        self._release_scope()


class _TypeOverride(Override):
    def __init__(
        self,
        trait_type: type[Overridable],
        scope: type[PropertyClass] | PropertyClass,
    ):
        super().__init__(trait_type, scope)
        target_type, override_factory = (
            (type(scope), lambda t, p: _InstanceOverride(t, scope))
            if isinstance(scope, PropertyClass)
            else (scope, Override)
        )

        self._property_overrides = [
            *itertools.chain.from_iterable(
                (override_factory(t, p) for t in p.traits if isinstance(t, trait_type))
                for p in target_type.properties
            )
        ]

    def _apply(self):
        for po in self._property_overrides:
            po.__enter__()

    def _revert(self):
        for po in self._property_overrides:
            po.__exit__(None, None, None)


class _InstanceOverride(Override):
    def __init__(self, subject: Overridable, instance: PropertyClass):
        super().__init__(subject, instance)

    def _override(self, instance, *args, **kwargs):
        return (
            self.subject._override
            if instance is self._scope and self._thread_id == _current_thread_id()
            else self.subject._override_target
        )(instance, *args, **kwargs)


class Overridable(Trait):
    def __init__(self, target: Callable):
        super().__init__()
        self._override_target = target

    @abstractmethod
    def _override(self, *args, **kwargs):
        """Execute alternate behavior while Trait is overridden."""

    def override(self, instance: PropertyClass = None):
        scope = self.subject if instance is None else instance
        override_type = self._override_type_registry[type(scope) :]
        return override_type(self, scope)

    @classmethod
    def override_all(cls, scope: type[PropertyClass] | PropertyClass) -> Override:
        return _TypeOverride(cls, scope)

    _override_type_registry = TypeRegistry[type[Override]](
        {
            PropertyType: _TypeOverride,
            Property: Override,
            PropertyClass: _InstanceOverride,
        }
    )
