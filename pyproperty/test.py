from unittest import TestCase
from pyproperty.property import (
    Property,
    PropertyClass,
    InstanceMethodDefault,
    ClassMethodDefault,
    overridable,
)


class Example(PropertyClass):
    def _default_a(self):
        return self.b * self.c

    a = Property[float](default=InstanceMethodDefault(_default_a))

    @classmethod
    def _default_b(cls):
        return 1

    b = Property[float](default=ClassMethodDefault(_default_b))
    c = Property[int](default=1)

    def _get_d(self):
        return self.a + self.b + self.c

    d = Property[float](getter=overridable(_get_d))


class PropertyTest(TestCase):
    def test_init(self):
        ex = Example()
        self.assertEqual(1, ex.a)
        self.assertEqual(1, ex.b)
        self.assertEqual(1, ex.c)

        ex = Example(b=2, c=3)
        self.assertEqual(6, ex.a)
        self.assertEqual(2, ex.b)
        self.assertEqual(3, ex.c)

        ex = Example(a=1, b=2, c=3)
        self.assertEqual(1, ex.a)
        self.assertEqual(2, ex.b)
        self.assertEqual(3, ex.c)

    def test_property_value_type(self):
        self.assertEqual(Example.a.value_type, float)
        self.assertEqual(Example.b.value_type, float)
        self.assertEqual(Example.c.value_type, int)

    def test_overrides(self):
        sentinel = object()
        ex = Example()
        self.assertEqual(3, ex.d)

        class Child(Example):
            def _default_a(self):
                return sentinel

            def _get_d(self):
                return sentinel

        c = Child()
        self.assertIs(sentinel, c.a)
        self.assertIs(sentinel, c.d)
