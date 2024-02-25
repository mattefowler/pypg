from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any

from pypg import PreSet, PropertyClass
from pypg.property import DataModifierMixin


class ReferenceCounted(PropertyClass, ABC):
    """A type that counts the number of places it has been composed as a
    Property value."""

    class _ReferenceCounter(DataModifierMixin[PreSet]):
        def apply(self, instance: PropertyClass, value) -> Any:
            current = self._get_current_value(instance)
            if isinstance(current, ReferenceCounted):
                current._dereference(instance)
            if isinstance(value, ReferenceCounted):
                value._reference(instance)
            return value

        def _get_current_value(self, instance):
            try:
                return instance.__dict__[self.subject.attribute_key]
            except KeyError:
                return None

    def _reference(self, instance: PropertyClass) -> None:
        self.__composers.add(instance)

    def _dereference(self, instance: PropertyClass) -> None:
        self.__composers.remove(instance)
        if not self.__composers:
            self._on_unreferenced()

    @property
    def reference_count(self) -> int:
        return len(self.__composers)

    @property
    def composed_by(self) -> set[PropertyClass]:
        return self.__composers.copy()

    @cached_property
    def __composers(self) -> set:
        return set()

    @abstractmethod
    def _on_unreferenced(self):
        """
        override this method to implement behavior that should occur
        when reference count decreases to 0.
        """

    @classmethod
    def intrinsic_traits(cls):
        return (cls._ReferenceCounter(),)
