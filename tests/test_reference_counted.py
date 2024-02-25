from unittest import TestCase

from pypg import Property, PropertyClass
from pypg.traits.reference_counted import ReferenceCounted


class Composed(ReferenceCounted):
    i = Property[int](0)
    flag = Property[bool](False)

    def _on_unreferenced(self):
        self.flag = True


class Composer(PropertyClass):
    prop = Property[Composed]()


class TestReferenceCounted(TestCase):
    def test_reference_counted(self):
        composed = Composed()
        composers = [Composer(prop=composed) for _ in range(4)]
        ref_set = {*composers}
        self.assertEqual(ref_set, composed.composed_by)

        for c in composers:
            self.assertFalse(composed.flag)
            c.prop = None
            ref_set.remove(c)
            self.assertEqual(ref_set, composed.composed_by)
        self.assertTrue(composed.flag)
