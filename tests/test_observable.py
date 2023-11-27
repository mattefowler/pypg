from unittest import TestCase

from pypg import PostGet, PostSet, Property, PropertyClass
from pypg.traits.observable import (
    Always,
    AsynchronousDelivery,
    Observable,
    OnChange,
    SynchronousDelivery,
    watch,
)


class WatchIt(PropertyClass):
    p = Property[int](traits=Observable[PostSet]())
    g = Property[int](default=0, traits=Observable[PostGet]())


class ObservableTest(TestCase):
    def setUp(self) -> None:
        self.w0 = WatchIt()
        self.w0_data = []
        self.w1 = WatchIt()
        self.w1_data = []

    def test_asynchronous_delivery(self):
        w0_delivery = AsynchronousDelivery(self.w0_data.append, OnChange())
        w1_delivery = AsynchronousDelivery(self.w1_data.append, OnChange())
        with (
            watch(self.w0, "p", w0_delivery) as w_subscription,
            watch(self.w1, "p", w1_delivery) as w2_subscription,
        ):
            self.w0.p = 0
            self.assertTrue(w0_delivery.await_delivery(2))
            self.assertEqual([0], self.w0_data)

            self.w0.p = 1
            self.assertTrue(w0_delivery.await_delivery(2))
            self.assertEqual([0, 1], self.w0_data)

            self.assertFalse(w1_delivery.await_delivery(0))
            self.assertFalse(self.w1_data)

            self.w1.p = 1
            self.assertTrue(w1_delivery.await_delivery(2))
            self.assertEqual([1], self.w1_data)

            self.w0.p = 0
            self.assertTrue(w0_delivery.await_delivery(2))
            self.assertEqual([0, 1, 0], self.w0_data)

    def test_synchronous_delivery(self):
        with (
            watch(
                self.w0,
                "p",
                SynchronousDelivery(self.w0_data.append, OnChange()),
            ) as w_subscription,
            watch(
                self.w1,
                "p",
                SynchronousDelivery(self.w1_data.append, OnChange()),
            ) as w2_subscription,
        ):
            self.w0.p = 0
            self.assertEqual([0], self.w0_data)
            self.assertFalse(self.w1_data)

            self.w1.p = 1
            self.assertEqual([1], self.w1_data)
            self.assertEqual([0], self.w0_data)
        # redundant cancellation does no harm
        w_subscription.cancel()

    def test_always_update(self):
        with watch(
            self.w0,
            WatchIt.g,
            SynchronousDelivery(self.w0_data.append, Always()),
        ):
            for i in range(1, 5):
                self.assertEqual([self.w0.g] * i, self.w0_data)

    def test_error_handling(self):
        ex = RuntimeError()

        def exception_in_callback(*_):
            raise ex

        caught = []

        def handle_exception(value, ex):
            caught.append((value, ex))

        w0_delivery = AsynchronousDelivery(
            exception_in_callback, Always(), on_error=handle_exception
        )

        with watch(self.w0, WatchIt.p, w0_delivery):
            value = 1234
            self.w0.p = 1234
            self.assertTrue(w0_delivery.await_delivery(2))
            self.assertEqual([(value, ex)], caught)

    def test_multiple_modifier_triggers(self):
        class C(PropertyClass):
            p = Property[int](traits=[Observable[PostSet, PostGet]()])

        c = C()
        delivered = []
        expected = [1]
        with Observable.watch(c, C.p, SynchronousDelivery(delivered.append, Always())):
            c.p = 1
            for i in range(3):
                expected.append(c.p)
        self.assertEqual(expected, delivered)
