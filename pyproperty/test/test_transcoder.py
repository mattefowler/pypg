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

        i0, i1, i2 = (
            TestClass(a=0, b=1),
            TestClass(a=1, b=2),
            TestClass(a=2, b=3),
        )
        i0.c[i0] = [i1, i2]
        i2.c[i1] = [i2, i0]
        i1.c[i2] = [i0, i1]
        encoded = encode(i0)
        i0_copy = decode(encoded)
        i0c, i1c, i2c = i0_copy.c[i0_copy]
        self.assertIs(i0_copy, i0c)
        self.assertEqual([i0c, i1c], i1c.c[i2c])
        self.assertEqual([i2c, i1c, i0c], i1c.c[i1c])
