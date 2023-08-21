from unittest import TestCase

from pypg import (
    MethodReference,
    PostSet,
    Property,
    PropertyClass,
)
from pypg.traits import Observable, Unit


class Example(PropertyClass):
    def default_poly(self, offset):
        return self.b * self.c + offset

    a = Property[float](default=MethodReference(default_poly, offset=1))
    a2 = Property[float](default=MethodReference(default_poly, offset=2))

    @classmethod
    def default_gain(cls):
        return 1

    b = Property[float](default=MethodReference(default_gain))

    @classmethod
    def _optional_c_traits(cls):
        pass

    c = Property[int](default=1, traits=_optional_c_traits)

    def default_sum(self):
        return self.a + self.b + self.c

    @classmethod
    def _d_traits(cls):
        return Unit("mm"), Observable[PostSet]()

    d = Property[float](
        default=1, getter=MethodReference(default_sum), traits=_d_traits
    )


class PropertyTest(TestCase):
    def test_method_reference(self):
        mr = MethodReference(Example.default_poly)
        ex = Example()
        self.assertEqual(ex.default_poly(offset=10), mr(ex, offset=10))

    def test_declaring_type(self):
        self.assertEqual(Example.a.declaring_type, Example)

    def test_init(self):
        ex = Example()
        self.assertEqual(2, ex.a)
        self.assertEqual(3, ex.a2)
        self.assertEqual(1, ex.b)
        self.assertEqual(1, ex.c)

        ex = Example(b=2, c=3)
        self.assertEqual(7, ex.a)
        self.assertEqual(8, ex.a2)
        self.assertEqual(2, ex.b)
        self.assertEqual(3, ex.c)

        ex = Example(a=1, b=2, c=3)
        self.assertEqual(1, ex.a)
        self.assertEqual(8, ex.a2)
        self.assertEqual(2, ex.b)
        self.assertEqual(3, ex.c)

    def test_property_accessors(self):
        ex = Example()
        a = Example.a
        a.set(ex, 12)
        self.assertEqual(12, ex.a)
        self.assertEqual(12, a.get(ex))

        class Foo:
            pass

        foo = Foo()

        with self.assertRaises(AttributeError):
            a.get(foo)

    def test_property_str(self):
        self.assertEqual("test_property.Example.a", str(Example.a))

    def test_property_value_type(self):
        self.assertIsInstance(Example.a, Property)
        self.assertIsInstance(Example.b, Property)
        self.assertIsInstance(Example.c, Property)
        self.assertEqual(Example.a.value_type, float)
        self.assertEqual(Example.b.value_type, float)
        self.assertEqual(Example.c.value_type, int)

    def test_config_init_exception(self):
        class C(PropertyClass):
            a = Property()

        cfg = {"a": 0, "b": 1}
        invalid = {"b": cfg["b"]}
        try:
            C(**cfg)
        except TypeError as te:
            self.assertIn(str(invalid), str(te))
