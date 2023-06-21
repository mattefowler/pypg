from unittest import TestCase
from operator import ge, le, lt, gt

from pypg import PreSet, Property, PropertyClass
from pypg.traits.allowed_range import AllowedRange


class TestAllowedRange(TestCase):
    def test_exclusive_bounds(self):
        class Bounded(PropertyClass):
            ar = AllowedRange[PreSet](0, 1)
            p = Property[float](0.5, traits=[ar])

        b = Bounded()
        b.p = 0.5  # within range
        b.p = 0  # boundaries are inclusive by default
        b.p = 1  # boundaries are inclusive by default
        with self.assertRaises(ValueError):
            b.p = -1  # below minimum
        with self.assertRaises(ValueError):
            b.p = 2  # above maximum

    def test_exclusive_bounds(self):
        class Bounded(PropertyClass):
            ar = AllowedRange[PreSet](0, 1, min_cmp=gt, max_cmp=lt)
            p = Property[float](0.5, traits=[ar])

        b = Bounded()
        b.p = 0.5  # within range
        with self.assertRaises(ValueError):
            b.p = 0  # bounds have been explicitly declared exclusive
        with self.assertRaises(ValueError):
            b.p = 1  # bounds have been explicitly declared exclusive
        with self.assertRaises(ValueError):
            b.p = -1  # below minimum
        with self.assertRaises(ValueError):
            b.p = 2  # above maximum

    def test_operators_exclusive(self):
        class Bounded(PropertyClass):
            ar = (AllowedRange[PreSet] < 1) > 0
            p = Property[float](0.5, traits=[ar])

        b = Bounded()
        b.p = 0.5  # within range
        with self.assertRaises(ValueError):
            b.p = 0  # boundaries are exlcusive by default
        with self.assertRaises(ValueError):
            b.p = 1  # boundaries are exlcusive by default
        with self.assertRaises(ValueError):
            b.p = -1  # below minimum
        with self.assertRaises(ValueError):
            b.p = 2  # above maximum

        class Bounded(PropertyClass):
            ar = (AllowedRange[PreSet] > 0) < 1
            p = Property[float](0.5, traits=[ar])

        b = Bounded()
        b.p = 0.5  # within range
        with self.assertRaises(ValueError):
            b.p = 0  # boundaries are exlcusive by default
        with self.assertRaises(ValueError):
            b.p = 1  # boundaries are exlcusive by default
        with self.assertRaises(ValueError):
            b.p = -1  # below minimum
        with self.assertRaises(ValueError):
            b.p = 2  # above maximum

    def test_operators_inclusive(self):
        class Bounded(PropertyClass):
            ar = (AllowedRange[PreSet] <= 1) >= 0
            p = Property[float](0, traits=[ar])

        b = Bounded()
        b.p = 0.5  # within range
        b.p = 0  # bounds have been explicitly declared inclusive
        b.p = 1  # bounds have been explicitly declared inclusive
        with self.assertRaises(ValueError):
            b.p = -1  # below minimum
        with self.assertRaises(ValueError):
            b.p = 2  # above maximum

        class Bounded(PropertyClass):
            ar = (AllowedRange[PreSet] >= 0) <= 1
            p = Property[float](0, traits=[ar])

        b = Bounded()
        b.p = 0.5  # within range
        b.p = 0  # bounds have been explicitly declared inclusive
        b.p = 1  # bounds have been explicitly declared inclusive
        with self.assertRaises(ValueError):
            b.p = -1  # below minimum
        with self.assertRaises(ValueError):
            b.p = 2  # above maximum

    def test_less_than_only(self):
        class Bounded(PropertyClass):
            p = Property[float](0, traits=[AllowedRange[PreSet] <= 1])

        b = Bounded()
        b.p = -1  # below maximum
        with self.assertRaises(ValueError):
            b.p = 2  # above maximum

    def test_greater_than_only(self):
        class Bounded(PropertyClass):
            p = Property[float](0, traits=[AllowedRange[PreSet] >= 0])

        b = Bounded()
        b.p = 0  # at minimum
        b.p = 2  # above minimum
        with self.assertRaises(ValueError):
            b.p = -1  # below minimum
