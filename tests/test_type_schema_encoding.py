from pprint import pprint
from unittest import TestCase

from pypg import Property, decode, encode
from tests.test_property import Example


class ComplexExample(Example):
    ex = Property[Example]()
    ex2 = Property[Example]()


class TypeSchemaEncodingTest(TestCase):
    def test_property_type_encoding(self):
        enc = encode(ComplexExample)
        pprint(enc)

    def test_type_transcoding(self):
        enc = encode(int)
        self.assertEqual(['type', 'int'], enc)
        self.assertIs(int, decode(enc))