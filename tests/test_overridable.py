from threading import Event, Thread
from unittest import TestCase

from pypg import MethodReference, PreSet, Property, PropertyClass
from pypg.traits import Validated


class OverrideTester(PropertyClass):
    def _validate(self, value):
        if value < 0:
            raise ValueError()

    p_validation = Validated[PreSet](MethodReference(_validate))
    p = Property[float](default=0, traits=p_validation)
    q_validation = Validated[PreSet](MethodReference(_validate))
    q = Property[float](default=0, traits=q_validation)


class TestOverridable(TestCase):
    def test_property_override(self):
        with self.assertRaises(ValueError):
            OverrideTester(p=-1)
        with OverrideTester.p_validation.override():
            OverrideTester(p=-1)
            with self.assertRaises(ValueError):
                OverrideTester(p=-1, q=-1)

            with OverrideTester.q_validation.override():
                OverrideTester(p=-1, q=-1)

            with self.assertRaises(ValueError):
                OverrideTester(p=-1, q=-1)
            OverrideTester(p=-1)
        with self.assertRaises(ValueError):
            OverrideTester(p=-1)

    def test_instance_override(self):
        ot = OverrideTester()
        ot2 = OverrideTester()
        with self.assertRaises(ValueError):
            ot.p = -1
        with OverrideTester.p_validation.override(ot):
            ot.p = -1
            with self.assertRaises(ValueError):
                ot2.p = -1
            with self.assertRaises(ValueError):
                ot.q = -1
            with OverrideTester.q_validation.override(ot):
                ot.q = -1
                with self.assertRaises(ValueError):
                    ot2.p = -1
            with self.assertRaises(ValueError):
                ot.q = -1
            ot.p = -2
        with self.assertRaises(ValueError):
            ot.p = -1
        self.assertEqual(-2, ot.p)
        self.assertEqual(-1, ot.q)

    def test_multiple_override_scopes(self):
        with Validated.override_all(OverrideTester):
            ot = OverrideTester(p=-1, q=-1)
            with OverrideTester.p_validation.override(ot):
                ot.p = "a"
                with Validated.override_all(OverrideTester):
                    ot.q = "q"
                    with OverrideTester.p_validation.override(ot):
                        ot.p = "a"
            ot.p = "b"
        with self.assertRaises(ValueError):
            ot.p = -1
        ot.p = 1

    def test_thread_scope(self):
        bg_coordinator = Event()
        main_coordinator = Event()
        ot = OverrideTester()

        def bgworker():
            bg_coordinator.wait()
            bg_coordinator.clear()
            try:
                # main thread has override, this thread does not
                with self.assertRaises(ValueError):
                    ot.p = -1
                with OverrideTester.p_validation.override(ot):
                    # both threads have overrides
                    self.assertEqual(-2, ot.p)
                    main_coordinator.set()
                    ot.p = -1
                    bg_coordinator.wait()
                    bg_coordinator.clear()
            finally:
                main_coordinator.set()

        separate_thread = Thread(target=bgworker)
        separate_thread.start()
        with OverrideTester.p_validation.override(ot):
            # this thread has overrides, background does not
            ot.p = -2
            bg_coordinator.set()
            main_coordinator.wait()
            main_coordinator.clear()
        # bg thread has override, this does not
        with self.assertRaises(ValueError):
            ot.p = -1
        bg_coordinator.set()
        separate_thread.join()

    def test_override_all(self):
        with Validated.override_all(OverrideTester):
            ot = OverrideTester(p=-1, q=-1)
        with self.assertRaises(ValueError):
            ot.p = -2
        ot2 = OverrideTester()
        with Validated.override_all(ot):
            ot.p = -2
            ot.p = -2
            with self.assertRaises(ValueError):
                ot2.p = -1
