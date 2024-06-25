import os
import tempfile
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from operator import attrgetter
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
from pypg.traits.config import Config
from pypg.transcode import from_file, from_string, to_file, to_string, Decoder


class TestClass(PropertyClass):
    a = Property[int](default=0)
    b = Property[float](default=0)
    c = Property[dict[PropertyClass, list[PropertyClass]]](
        default=FunctionReference(lambda *_: {})
    )
    now = Property[datetime](default=lambda _: datetime.now())


class CallableTest(PropertyClass):
    delegate = Property[Callable[[], None]]()

    def some_method(self):
        return self


class EnumTest(PropertyClass):
    class E(Enum):
        A = 0
        B = 1
        C = 2

    enum_prop = Property[E]()


class Data(PropertyClass):
    value: str = Property[str](traits=[Config()])


class LargeCollectionExample(PropertyClass):
    list_prop: list[Data] = Property[list[Data]](traits=[Config()])


def free_function():
    pass


class TranscoderTest(TestCase):
    def test_registration(self):
        self.assertIs(DictEncoder, Encoder[dict])

    def test_transcoding(self):
        objs = [*range(4)]
        encoded = encode(objs)
        copy = decode(encoded)
        self.assertEqual(objs, copy)
        d = {1234: objs, 4321: objs, "asdf": 1234, 0: None}
        encoded = encode(d)
        copy = decode(encoded)
        self.assertIs(copy[1234], copy[4321])
        self.assertEqual(copy["asdf"], 1234)
        self.assertIsNone(copy[0])

    def test_propertyclass_transcoding(self):
        i0 = TestClass(a=0, b=1)
        i1 = TestClass(a=1, b=2, c={i0: [i0]})
        i2 = TestClass(a=2, b=3, c={i1: [i0, i1]})
        encoded = encode(i2)
        i2c = decode(encoded)
        self.assertEqual(i2c.now, i2.now)
        ((i1c, [i0c, _i1c]),) = i2c.c.items()
        self.assertIs(i1c, _i1c)
        ((_i0c, [__i0c]),) = i1c.c.items()
        self.assertIs(i0c, _i0c)
        self.assertIs(_i0c, __i0c)

    def test_to_from_file(self):
        ex = LargeCollectionExample()
        with tempfile.TemporaryDirectory() as temp_path:
            temp_file = os.path.join(temp_path, "encoded.json")
            to_file(ex, temp_file)
            copy = from_file(temp_file)
            self.assertIsInstance(copy, LargeCollectionExample)

    def test_to_from_string(self):
        ex = LargeCollectionExample()
        s = to_string(ex)
        copy = from_string(s)
        self.assertIsInstance(copy, LargeCollectionExample)

    def test_invalid_type_decoding(self):
        class LocalType(LargeCollectionExample):
            pass

        lt = LocalType()
        e = encode(lt)
        with self.assertRaises(TypeError):
            decode(e)

    def test_decode_override(self):
        class ExampleOverrider(Decoder):
            def _decode(self, obj_type: type, value: Any) -> Any:
                return "asdf"

        ex = LargeCollectionExample()
        encoded = encode(ex)
        asdf = decode(
            encoded, overrides={LargeCollectionExample: ExampleOverrider}
        )
        self.assertEqual("asdf", asdf)

    def test_enum_transcoding(self):
        e = EnumTest.E.A
        encoded = encode(e)
        copy = decode(encoded)
        self.assertEqual(e, copy)

        et = EnumTest(enum_prop=EnumTest.E.A)
        encoded = encode(et)
        copy = decode(encoded)
        self.assertEqual(et.enum_prop, copy.enum_prop)

    def test_reference_interning(self):
        ex = LargeCollectionExample(
            list_prop=[
                *[Data(value="hello")] * 10000,
                *[Data(value="world")] * 10000,
            ]
        )
        # In-Memory Round-Trip
        serialized = Config.encode(ex)
        deserialized: LargeCollectionExample = decode(serialized)
        deserialized_list = [*map(attrgetter("value"), deserialized.list_prop)]
        original_list = [*map(attrgetter("value"), ex.list_prop)]
        self.assertEqual(original_list, deserialized_list)

    def test_callable_serialization(self):
        objects = [
            i1 := CallableTest(delegate=free_function),
            i2 := CallableTest(delegate=i1.some_method),
        ]
        i1_copy, i2_copy = decode(encode(objects))
        self.assertIs(i1_copy.delegate, free_function)
        self.assertIs(i1_copy, i2_copy.delegate())

        with self.subTest("test closure-like de/serialization"):
            copy: CallableTest = decode(encode(i2))
            result = copy.delegate()
            self.assertIsInstance(result, CallableTest)
            self.assertIs(result.delegate, free_function)

    def test_id_provider(self):
        obj = Data(value='test')
        serialized = encode(obj, id_provider=id)
        [_, [_, obj_id]] = serialized
        self.assertEqual(obj_id, id(obj))
        copy = decode(serialized)
        self.assertEqual(obj.value, copy.value)