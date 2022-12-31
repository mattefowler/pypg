from unittest import TestCase

from pypg import decode, encode
from tests.test_property import Example


class TypeSchemaEncodingTest(TestCase):
    def test_encoding(self):
        enc = encode(Example)
        from pprint import pprint

        pprint(enc)

    def test_type_transcoding(self):
        enc = encode(int)
        intid = str(id(int))
        expected = {"root": intid, intid: ["type", str(int.__name__)]}
        self.assertEqual(expected, enc)
        self.assertIs(int, decode(enc))
