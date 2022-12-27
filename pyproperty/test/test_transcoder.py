import os
import tempfile
from os.path import basename
from unittest import TestCase

from pyproperty import (
    DictEncoder,
    Encoder,
    Property,
    PropertyClass,
    decode,
    encode,
    FunctionReference,
)
from pyproperty.test.test_property import Example
from pyproperty.transcode import from_file, from_string, to_file, to_string


class TestClass(PropertyClass):
    a = Property[int](default=0)
    b = Property[float](default=0)
    c = Property[dict[PropertyClass, list[PropertyClass]]](
        default=FunctionReference(lambda *_: {})
    )


class TranscoderTest(TestCase):
    def test_registration(self):
        self.assertIs(DictEncoder, Encoder[dict])

    def test_transcoding(self):
        objs = [*range(4)]
        encoded = encode(objs)
        expected = {
            "root": str(id(objs)),
            str(id(objs)): [list.__name__, [str(id(i)) for i in objs]],
            **{str(id(i)): [type(i).__name__, i] for i in objs},
        }
        self.assertEqual(expected, encoded)
        copy = decode(encoded)
        self.assertEqual(objs, copy)
        d = {1234: objs, 4321: objs, "asdf": 1234}
        encoded = encode(d)
        copy = decode(encoded)
        self.assertIs(d[1234], d[4321])
        self.assertEqual(d["asdf"], 1234)

    def test_propertyclass_transcoding(self):

        i0 = TestClass(a=0, b=1)
        i1 = TestClass(a=1, b=2, c={i0: [i0]})
        i2 = TestClass(a=2, b=3, c={i1: [i0, i1]})
        encoded = encode(i2)
        i2c = decode(encoded)
        ((i1c, [i0c, _i1c]),) = i2c.c.items()
        self.assertIs(i1c, _i1c)
        ((_i0c, [__i0c]),) = i1c.c.items()
        self.assertIs(i0c, _i0c)
        self.assertIs(_i0c, __i0c)

    def test_to_from_file(self):
        ex = Example()
        with tempfile.TemporaryDirectory() as temp_path:
            temp_file = os.path.join(temp_path, "encoded.json")
            to_file(ex, temp_file)
            copy = from_file(temp_file)
            self.assertIsInstance(copy, Example)

    def test_to_from_string(self):
        ex = Example()
        s = to_string(ex)
        copy = from_string(s)
        self.assertIsInstance(copy, Example)
