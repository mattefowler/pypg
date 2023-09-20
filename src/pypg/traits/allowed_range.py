from __future__ import annotations

from abc import ABCMeta
from operator import lt, le, gt, ge
from typing import Callable

from pypg import PropertyClass
from pypg.traits import Validated

Comparator = Callable[[float, float], bool]
LimitProvider = float | Callable[[PropertyClass], float] | None


class _AllowedRangeMeta(ABCMeta):
    def __lt__(self, other: LimitProvider):
        return self(None, other, max_cmp=lt)

    def __le__(self, other: LimitProvider):
        return self(None, other, max_cmp=le)

    def __gt__(self, other: LimitProvider):
        return self(other, None, min_cmp=gt)

    def __ge__(self, other: LimitProvider):
        return self(other, None, min_cmp=ge)


class AllowedRange(Validated, metaclass=_AllowedRangeMeta):
    def __init__(
        self,
        minimum: LimitProvider,
        maximum: LimitProvider,
        min_cmp: Comparator = ge,
        max_cmp: Comparator = le,
    ):
        super().__init__(self.check_range)
        self.minimum, self.maximum = (
            bound if callable(bound) else self._constant(bound)
            for bound in (minimum, maximum)
        )
        self.min_cmp = min_cmp
        self.max_cmp = max_cmp

    @staticmethod
    def _constant(value):
        return lambda _: value

    def check_range(self, instance: PropertyClass, value: float):
        min_val = self.minimum(instance)
        max_val = self.maximum(instance)
        min_check = min_val, self.min_cmp
        max_check = max_val, self.max_cmp
        if not all(
            bound is None or cmp(value, bound) for bound, cmp in (min_check, max_check)
        ):
            raise ValueError(
                f"{value} outside allowed range for {self.subject}: {min_val},{max_val}"
            )

    def __lt__(self, other: AllowedRange | LimitProvider):
        return type(self)(
            self.minimum,
            (other.minimum if isinstance(other, AllowedRange) else other),
            self.min_cmp,
            lt,
        )

    def __gt__(self, other: AllowedRange | LimitProvider):
        return type(self)(
            (other.maximum if isinstance(other, AllowedRange) else other),
            self.maximum,
            gt,
            self.max_cmp,
        )

    def __le__(self, other: AllowedRange | LimitProvider):
        return type(self)(
            self.minimum,
            (other.minimum if isinstance(other, AllowedRange) else other),
            self.min_cmp,
            le,
        )

    def __ge__(self, other: AllowedRange | LimitProvider):
        return type(self)(
            (other.maximum if isinstance(other, AllowedRange) else other),
            self.maximum,
            ge,
            self.max_cmp,
        )
