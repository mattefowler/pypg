from unittest import TestCase

from pypg import Property, PropertyClass
from pypg.traits import Obligate


class TestObligate(TestCase):
    def test_obligate(self):
        class ObligateDataTest(PropertyClass):
            obligate = Obligate()
            required_data = Property[int](traits=obligate)

        ObligateDataTest(required_data=0)

        with self.assertRaises(ValueError):
            odt = ObligateDataTest()

        with ObligateDataTest.obligate.override():
            odt = ObligateDataTest()

        self.assertIs(odt.required_data, None)