from threading import Event
from unittest import TestCase
from pyproperty.property import (
    PostSet,
    Property,
    PropertyClass,
    MethodReference
)
from pyproperty.traits import (
    AsynchronousDelivery,
    Observable,
    OnChange,
    SynchronousDelivery,
    Unit,
    watch,
)


class Example(PropertyClass):
    def _default_a(self):
        return self.b * self.c

    a = Property[float](default=MethodReference(_default_a))

    @classmethod
    def _default_b(cls):
        return 1

    b = Property[float](default=MethodReference(_default_b))
    c = Property[int](default=1)

    def _get_d(self):
        return self.a + self.b + self.c

    @classmethod
    def _d_traits(cls):
        return Unit("mm")

    d = Property[float](getter=MethodReference(_get_d), traits=_d_traits)


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
        self.assertIsInstance(Example.a, Property)
        self.assertIsInstance(Example.b, Property)
        self.assertIsInstance(Example.c, Property)
        self.assertEqual(Example.a.value_type, float)
        self.assertEqual(Example.b.value_type, float)
        self.assertEqual(Example.c.value_type, int)

    def test_overrides(self):
        sentinel = object()
        ex = Example()
        self.assertEqual(3, ex.d)
        (ex_unit,) = Example.d.traits
        self.assertIsInstance(ex_unit, Unit)
        self.assertEqual(ex_unit.unit, "mm")

        class Child(Example):
            def _default_a(self):
                return sentinel

            def _get_d(self):
                return sentinel

            @classmethod
            def _d_traits(cls):
                return Unit("in")

        c = Child()
        self.assertIs(sentinel, c.a)
        self.assertIs(sentinel, c.d)
        (c_unit,) = Child.d.traits
        self.assertEqual(c_unit.unit, "in")

    def test_observable(self):
        class WatchIt(PropertyClass):
            p = Property[int](traits=Observable[PostSet]())

        def create_test_objects():
            received = []
            event = Event()

            def receiver(value):
                received.append(value)
                event.set()

            return WatchIt(), received, event, receiver

        w0, w0_data, w0_event, w0_receiver = create_test_objects()
        w1, w1_data, w1_event, w1_receiver = create_test_objects()
        with (
            watch(
                w0, "p", AsynchronousDelivery(w0_receiver, OnChange())
            ) as w_subscription,
            watch(
                w1, "p", AsynchronousDelivery(w1_receiver, OnChange())
            ) as w2_subscription,
        ):
            w0.p = 0
            self.assertTrue(w0_event.wait(2))
            self.assertEqual([0], w0_data)

            self.assertFalse(w1_event.is_set())
            self.assertFalse(w1_data)
            w0_event.clear()

            w1.p = 1
            self.assertTrue(w1_event.wait(1))
            self.assertEqual([1], w1_data)

            self.assertFalse(w0_event.is_set())
            self.assertEqual([0], w0_data)

        w0_data.clear()
        w1_data.clear()

        with (
            watch(
                w0, "p", SynchronousDelivery(w0_receiver, OnChange())
            ) as w_subscription,
            watch(
                w1, "p", SynchronousDelivery(w1_receiver, OnChange())
            ) as w2_subscription,
        ):
            w0.p = 0
            self.assertEqual([0], w0_data)
            self.assertFalse(w1_data)
            w0_event.clear()

            w1.p = 1
            self.assertEqual([1], w1_data)
            self.assertEqual([0], w0_data)
