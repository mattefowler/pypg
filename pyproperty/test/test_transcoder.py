from unittest import TestCase

from pyproperty import decode, encode


class TranscoderTest(TestCase):
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
