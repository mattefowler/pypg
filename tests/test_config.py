from unittest import TestCase

from pypg import PropertyClass, MethodReference, Property, decode
from pypg.traits.config import Config


class InnerCls(PropertyClass):
    p1 = Property[int](default=0, traits=[Config(True)])


class CfgDataCls(PropertyClass):
    def _make_inner(self):
        return InnerCls()

    inner = Property[InnerCls](default=MethodReference(_make_inner))
    excluded = Property[int](default=0, traits=[Config(False)])
    included = Property[int](default=0, traits=[Config(True)])
    excluded_inner = Property[InnerCls](traits=[Config(False)])


class ConfigTest(TestCase):
    def test_config(self):
        cdc = CfgDataCls(included=1, excluded=1, excluded_inner=InnerCls(p1=1))
        cdc.inner.p1 = 1
        encoded = Config.encode(cdc)
        copy = decode(encoded)
        self.assertEqual(1, copy.inner.p1)
        self.assertEqual(1, copy.included)

        self.assertEqual(0, copy.excluded)
        self.assertIsNone(copy.excluded_inner)