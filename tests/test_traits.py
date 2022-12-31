from unittest import TestCase

from pypg import MethodReference, PreSet
from tests.test_property import Example
from pypg.traits import Unit, Validated


class TestTraits(TestCase):
    def test_overrides(self):
        sentinel = object()
        ex = Example()
        self.assertEqual(4, ex.d)
        self.assertFalse(Example.c.traits)
        (ex_unit, *_) = Example.d.traits
        self.assertIsInstance(ex_unit, Unit)
        self.assertEqual(ex_unit.value, "mm")

        class Child(Example):
            def default_poly(self, offset):
                return sentinel

            def default_sum(self):
                return sentinel

            def _validate_d(self, value):
                assert value > 0

            @classmethod
            def _optional_c_traits(cls):
                return Unit("N")

            @classmethod
            def _d_traits(cls):
                return Unit("in"), Validated[PreSet](
                    MethodReference(cls._validate_d)
                )

        c = Child()
        self.assertIs(sentinel, c.a)
        self.assertIs(sentinel, c.d)
        (c_unit, validator) = Child.d.traits
        self.assertEqual(c_unit.value, "in")
        with self.assertRaises(AssertionError):
            c.d = -1
        with self.assertRaises(AssertionError):
            validator.apply(c, -1)
