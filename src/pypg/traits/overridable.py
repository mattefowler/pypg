from __future__ import annotations

__all__ = ["Overridable"]

import contextlib
import itertools
import threading
from abc import abstractmethod
from functools import wraps

from pypg import Property, PropertyClass, PropertyType, Trait

OverrideScope = PropertyType | PropertyClass | Property


def _current_thread_id():
    return threading.current_thread().native_id


_threadid = int
_context_count = int


class Overridable(Trait):
    def __init_subclass__(cls, **kwargs):
        try:
            override_target = kwargs.pop("override_target")
            setattr(
                cls,
                override_target,
                Overridable._Accessor(getattr(cls, override_target)),
            )
        except KeyError:
            pass
        super().__init_subclass__(**kwargs)

    def __init__(self):
        super().__init__()
        self._overrides: dict[
            _threadid, dict[PropertyClass, _context_count]
        ] = {}

    class _Accessor:
        def __init__(self, override_target):
            self.override_target = override_target

        class _OverrideCheck:
            def __init__(
                self,
                accessor: Overridable._Accessor,
                overridable: Overridable,
                overrides: dict[PropertyClass, int],
            ):
                self._trait = overridable
                self._accessor = accessor
                self._overrides = overrides
                wraps(self._accessor.override_target)

            def __call__(self, instance, *args, **kwargs):
                return (
                    self._trait._override
                    if instance in self._overrides
                    else self._accessor.override_target.__get__(
                        self._trait, self._trait.__class__
                    )
                )(instance, *args, **kwargs)

        def __get__(self, overridable: Overridable, owner):
            try:
                overrides = overridable._overrides[_current_thread_id()]
            except KeyError:
                return self.override_target.__get__(
                    overridable, overridable.__class__
                )
            return (
                self._OverrideCheck(self, overridable, overrides)
                if None not in overrides
                else overridable._override
            )

    @abstractmethod
    def _override(self, *args, **kwargs):
        """Execute alternate behavior while Trait is overridden."""

    @contextlib.contextmanager
    def override(self, instance: PropertyClass = None):
        tid = _current_thread_id()
        try:
            instance_dict = self._overrides[tid]
        except KeyError:
            instance_dict = {instance: 0}
            self._overrides[tid] = instance_dict
        try:
            instance_dict[instance] += 1
        except KeyError:
            instance_dict[instance] = 1
        yield
        count = instance_dict[instance] - 1
        if not count:
            instance_dict.pop(instance)
            if not instance_dict:
                self._overrides.pop(tid)
        else:
            instance_dict[instance] = count

    @classmethod
    @contextlib.contextmanager
    def override_all(cls, target: PropertyType | PropertyClass):
        scope, target_type = (
            (target, type(target))
            if isinstance(target, PropertyClass)
            else (None, target)
        )
        ctxs = [
            t.override(scope)
            for t in itertools.chain.from_iterable(
                (t for t in p.traits if isinstance(t, cls))
                for p in target_type.properties
            )
        ]
        for ctx in ctxs:
            ctx.__enter__()
        yield
        for ctx in ctxs:
            ctx.__exit__(None, None, None)
