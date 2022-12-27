from threading import Event
from unittest import TestCase
from pyproperty.property import (
    PostGet,
    PostSet,
    Property,
    PropertyClass,
    MethodReference,
)
from pyproperty.traits import (
    Always,
    AsynchronousDelivery,
    Observable,
    OnChange,
    SynchronousDelivery,
    Unit,
    Validator,
    watch,
)


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
        return Unit("mm")

    d = Property[float](
        default=1, getter=MethodReference(default_sum), traits=_d_traits
    )


class PropertyTest(TestCase):
    def test_method_reference(self):
        mr = MethodReference(Example.default_poly)
        ex = Example()
        self.assertEqual(ex.default_poly(offset=10), mr(ex, offset=10))

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

    def test_overrides(self):
        sentinel = object()
        ex = Example()
        self.assertEqual(4, ex.d)
        self.assertFalse(Example.c.traits)
        (ex_unit,) = Example.d.traits
        self.assertIsInstance(ex_unit, Unit)
        self.assertEqual(ex_unit.unit, "mm")

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
                return Unit("in"), Validator(MethodReference(cls._validate_d))

        c = Child()
        self.assertIs(sentinel, c.a)
        self.assertIs(sentinel, c.d)
        (c_unit, validator) = Child.d.traits
        self.assertEqual(c_unit.unit, "in")
        with self.assertRaises(AssertionError):
            c.d = -1
        with self.assertRaises(AssertionError):
            validator.apply(c, -1)

    def test_observable(self):
        class WatchIt(PropertyClass):
            p = Property[int](traits=Observable[PostSet]())
            g = Property[int](default=0, traits=Observable[PostGet]())

        w0 = WatchIt()
        w0_data = []
        w1 = WatchIt()
        w1_data = []
        w0_delivery = AsynchronousDelivery(w0_data.append, OnChange())
        w1_delivery = AsynchronousDelivery(w1_data.append, OnChange())
        with (
            watch(w0, "p", w0_delivery) as w_subscription,
            watch(w1, "p", w1_delivery) as w2_subscription,
        ):
            w0.p = 0
            self.assertTrue(w0_delivery.await_delivery(2))
            self.assertEqual([0], w0_data)

            self.assertFalse(w1_delivery.await_delivery(0))
            self.assertFalse(w1_data)

            w1.p = 1
            self.assertTrue(w1_delivery.await_delivery(2))
            self.assertEqual([1], w1_data)

            self.assertTrue(w0_delivery.await_delivery(0))
            self.assertEqual([0], w0_data)

        w0_data.clear()
        w1_data.clear()

        with (
            watch(
                w0, "p", SynchronousDelivery(w0_data.append, OnChange())
            ) as w_subscription,
            watch(
                w1, "p", SynchronousDelivery(w1_data.append, OnChange())
            ) as w2_subscription,
        ):
            w0.p = 0
            self.assertEqual([0], w0_data)
            self.assertFalse(w1_data)

            w1.p = 1
            self.assertEqual([1], w1_data)
            self.assertEqual([0], w0_data)
        # redundant cancellation does no harm
        w_subscription.cancel()

        w0_data.clear()
        with watch(
            w0, WatchIt.g, SynchronousDelivery(w0_data.append, Always())
        ):
            for i in range(1, 5):
                self.assertEqual([w0.g] * i, w0_data)

        ex = RuntimeError()

        def exception_in_callback(*_):
            raise ex

        caught = []

        def handle_exception(value, ex):
            caught.append((value, ex))

        w0_delivery = AsynchronousDelivery(
            exception_in_callback, Always(), on_error=handle_exception
        )

        with watch(w0, WatchIt.p, w0_delivery):
            value = 1234
            w0.p = 1234
            self.assertTrue(w0_delivery.await_delivery(2))
            self.assertEqual([(value, ex)], caught)
