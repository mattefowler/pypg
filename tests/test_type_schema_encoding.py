from unittest import TestCase

from pypg import decode, encode
from pypg.transcode import unpack
from tests.test_property import Example


class TypeSchemaEncodingTest(TestCase):
    def test_property_type_encoding(self):
        enc = encode(Example)
        ex_a_enc = encode(Example.a)
        self.assertEqual(enc[ex_a_enc["root"]], ex_a_enc[ex_a_enc["root"]])
        for t in Example.d.traits:
            self.assertIn(str(id(t)), enc)
        from pprint import pprint

        pprint(enc)

    def test_type_transcoding(self):
        enc = encode(int)
        intid = str(id(int))
        expected = {"root": intid, intid: ["type", str(int.__name__)]}
        self.assertEqual(expected, enc)
        self.assertIs(int, decode(enc))

    def test_unpack_schema(self):
        actual = unpack(encode(Example))
        expected = [
            "tests.test_property.Example",
            {
                "a": [
                    "pypg.property.Property",
                    {"value_type": ["type", "float"], "traits": []},
                ],
                "a2": [
                    "pypg.property.Property",
                    {"value_type": ["type", "float"], "traits": []},
                ],
                "b": [
                    "pypg.property.Property",
                    {"value_type": ["type", "float"], "traits": []},
                ],
                "c": [
                    "pypg.property.Property",
                    {"value_type": ["type", "int"], "traits": []},
                ],
                "d": [
                    "pypg.property.Property",
                    {
                        "value_type": ["type", "float"],
                        "traits": [
                            ["pypg.traits.unit.Unit", {"value": ["str", "mm"]}],
                            [
                                "pypg.traits.observable.Observable",
                                "['pypg.property.PostSet']",
                            ],
                        ],
                    },
                ],
            },
        ]
        self.assertEqual(expected, actual)
