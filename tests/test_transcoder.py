import os
import tempfile
from typing import Any
from unittest import TestCase

from pypg import (
    DictEncoder,
    Encoder,
    FunctionReference,
    Property,
    PropertyClass,
    decode,
    encode,
)
from tests.test_property import Example
from pypg.transcode import from_file, from_string, to_file, to_string, unpack, Decoder


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
        d = {1234: objs, 4321: objs, "asdf": 1234, 0: None}
        encoded = encode(d)
        copy = decode(encoded)
        self.assertIs(d[1234], d[4321])
        self.assertEqual(d["asdf"], 1234)
        self.assertIsNone(copy[0])

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

    def test_invalid_type_decoding(self):
        class LocalType(Example):
            pass

        lt = LocalType()
        e = encode(lt)
        with self.assertRaises(TypeError):
            decode(e)

    def test_unpack(self):
        ex = Example()
        enc_ex = encode(ex)
        ex_type_name, unpacked_ex_data = unpacked_ex = unpack(enc_ex)

        d = {ex: 0}  # note a non-string is being used as a key.
        enc_d = encode(d)
        unpacked_d = unpack(enc_d)
        typename, (unpacked_data,) = unpacked_d
        [
            (key_typename, key_obj_data),
            (value_typename, value_obj_data),
        ] = unpacked_data
        self.assertEqual(typename, dict.__name__)
        self.assertEqual(key_obj_data, unpacked_ex_data)
        self.assertEqual(value_typename, int.__name__)
        self.assertEqual(value_obj_data, 0)

        l = [ex, ex]
        enc_l = encode(l)
        enc_l_typename, [unpacked_ex_1, unpacked_ex_2] = unpack(enc_l)
        self.assertEqual(enc_l_typename, list.__name__)
        self.assertEqual(unpacked_ex, unpacked_ex_1)
        self.assertEqual(unpacked_ex_1, unpacked_ex_2)

    def test_decode_override(self):
        class ExampleOverrider(Decoder):
            def _decode(self, obj_type: type, value: Any) -> Any:
                return "asdf"

        ex = Example()
        encoded = encode(ex)
        asdf = decode(encoded, overrides={Example: ExampleOverrider})
        self.assertEqual("asdf", asdf)
