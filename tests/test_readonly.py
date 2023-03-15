from unittest import TestCase

from pypg import Property, PropertyClass
from pypg.traits import ReadOnly


class TestReadOnly(TestCase):
    def test_readonly(self):
        class Cls(PropertyClass):
            a_readonly = ReadOnly()
            a = Property[int](traits=a_readonly)
            b = Property[int]()

        c = Cls(a=0)
        self.assertEqual(c.a, 0)

        with self.assertRaises(PermissionError):
            c.a = 1234
        with Cls.a_readonly.override(c):
            c.a = 1234
        self.assertEqual(c.a, 1234)
