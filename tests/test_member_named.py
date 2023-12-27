from unittest import TestCase

from pypg import Property, PropertyClass
from pypg.named import Named
from pypg.traits.member_named import MemberNameElements


class Composer(PropertyClass):
    inner = Property[Named](lambda _: Named())


class ArrayComposer(PropertyClass):
    def _get_composers(self):
        return [Composer() for i in range(2)]

    composers = Property[list[Composer]](
        _get_composers, traits=[MemberNameElements()]
    )


class TestMemberNamed(TestCase):
    def test_member_named(self):
        composer = Composer()
        self.assertEqual(composer.inner.name, "inner")
        composer = Composer(inner=Named(name="test"))
        self.assertEqual(composer.inner.name, "test")

    def test_name_array(self):
        ac = ArrayComposer()
        for i, c in enumerate(ac.composers):
            self.assertEqual(c.name, f"composers {i}")
            self.assertEqual(c.inner.name, "inner")
