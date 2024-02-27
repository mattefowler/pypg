from unittest import TestCase

from pypg import PropertyClass, Property
from pypg.traits import ReadOnly


class Top(PropertyClass):
    top = Property[int](traits=[ReadOnly()])


class Left(Top):
    left = Property[int]()


class Right(Top):
    right = Property[int]()


class Bottom(Left, Right):
    bottom = Property[int]()


class TestDiamondInheritance(TestCase):
    def test_diamond(self):
        self.assertEqual(len(Bottom.properties), 4)
        Bottom()  # verify defaults are triggered once
        b = Bottom(top=1234)  # verify assignment is performed once
        self.assertEqual(b.top, 1234)
