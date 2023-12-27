from unittest import TestCase

from pypg import Property, PropertyClass
from pypg.named import Named


class Composer(PropertyClass):
    inner = Property[Named](lambda _: Named())


class TestMemberNamed(TestCase):
    def test_member_named(self):
        composer = Composer()
        self.assertEqual(composer.inner.name, "inner")
        composer = Composer(inner=Named(name="test"))
        self.assertEqual(composer.inner.name, "test")
