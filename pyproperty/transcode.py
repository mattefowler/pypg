from __future__ import annotations

__all__ = [
    "decode",
    "Decoder",
    "encode",
    "Encoder",
    "CollectionEncoder",
    "DictEncoder",
]

import json
from collections.abc import Collection, Iterable
from typing import Any, Union

from pyproperty.locator import Locator
from pyproperty.type_registry import TypeRegistry
from pyproperty.type_utils import get_fully_qualified_name

primitives = (str, int, float, bool)
Serializable = dict | list | Union[primitives]

_locator = Locator()


class _Transcoder:
    root_key = "root"

    _registry: TypeRegistry[_Transcoder] = None

    def __init_subclass__(
        cls, handler_for: type | Iterable[type] = (), **kwargs
    ):
        if isinstance(handler_for, type):
            handler_for = (handler_for,)
        if cls._registry is None:
            cls._registry = TypeRegistry()
        cls._registry.update({t: cls for t in handler_for})

    @classmethod
    def __class_getitem__(cls, obj_type: type) -> type[_Transcoder]:
        return cls._registry[obj_type:]


class Encoder(_Transcoder, handler_for=primitives):
    def __new__(cls, obj, parent: Encoder | None):
        encoder_type = cls[type(obj)]
        if encoder_type is cls:
            return super().__new__(cls)
        else:
            return encoder_type(obj, parent)

    def __init__(self, obj, parent: Encoder | None):
        self.parent = parent
        if parent is None:
            self.data: dict[str, str | list[str, Any]] = {}
        else:
            self.data = parent.data
        self.obj_id = self._pack(obj)
        if parent is None:
            self.data[self.root_key] = self.obj_id

    def _pack(self, obj) -> str:
        obj_id = str(id(obj))
        obj_type = type(obj)
        if obj_id not in self.data:
            encoded_data = [f"{get_fully_qualified_name(obj_type)}"]
            # pack data in 2 stages to prevent infinite recursion when encoding self-referential objects.
            self.data[obj_id] = encoded_data
            encoded_data.append(self._encode(obj))
        return obj_id

    def _encode(self, obj):
        return obj


class Decoder(_Transcoder, handler_for=primitives):
    def __new__(
        cls,
        encoded_data: dict,
        obj_id: str | None,
        locator: Locator,
        parent: Decoder | None,
    ):
        if obj_id is None:
            obj_id = encoded_data[cls.root_key]
        attr_type, attr_data = cls._unpack(encoded_data, obj_id, locator)
        decoder_cls = cls[attr_type]
        return (
            super().__new__(cls)
            if decoder_cls is cls
            else decoder_cls(encoded_data, obj_id, locator, parent)
        )

    def __init__(
        self,
        encoded_data: dict,
        obj_id: str | None,
        locator: Locator,
        parent: Decoder | None,
    ):
        self.parent = parent
        if parent is None:
            self.decoded_objects = {}
        else:
            self.decoded_objects = parent.decoded_objects
        self.encoded_data = encoded_data
        self.obj_id = (
            obj_id if obj_id is not None else encoded_data[self.root_key]
        )
        self.locator = locator
        self.instance = self.decode()

    def decode(self) -> Any:
        try:
            return self.decoded_objects[self.obj_id]
        except KeyError:
            pass

        member_type, member_data = self._unpack(
            self.encoded_data, self.obj_id, self.locator
        )
        instance = self._decode(member_type, member_data)
        self.decoded_objects[self.obj_id] = instance
        return instance

    @classmethod
    def _unpack(
        cls,
        encoded_data: dict[str, list[str, Any]],
        obj_id: str,
        locator: Locator,
    ) -> tuple[type, Any]:
        fully_qualified_name, value = encoded_data[obj_id]
        t = locator(fully_qualified_name)
        return t, value

    def _decode(self, obj_type: type, value: Any) -> Any:
        return obj_type(value)


def encode(obj) -> Any:
    return Encoder(obj, None).data


def to_string(obj) -> str:
    return json.dumps(encode(obj))


def from_string(encoded_object: str) -> Any:
    return decode(json.loads(encoded_object))


def to_file(obj, path: str):
    with open(path, "w") as f:
        json.dump(encode(obj), f)


def from_file(path: str, locator=_locator):
    with open(path) as f:
        return decode(json.load(f), locator)


def decode(obj_data, locator=_locator):
    return Decoder(
        obj_data, locator=locator, parent=None, obj_id=None
    ).instance


class TypeEncoder(Encoder, handler_for=type):
    pass


class CollectionEncoder(Encoder, handler_for=(tuple, set, list)):
    def _encode(self, obj: Collection):
        return [Encoder(item, self).obj_id for item in obj]


class CollectionDecoder(Decoder, handler_for=(tuple, set, list)):
    def _decode(self, obj_type, obj_ids: Collection[str]):
        return obj_type(
            (
                Decoder(self.encoded_data, obj_id, self.locator, self).instance
                for obj_id in obj_ids
            )
        )


class DictEncoder(Encoder, handler_for=dict):
    def _encode(self, obj: dict):
        return {
            Encoder(key, self).obj_id: Encoder(value, self).obj_id
            for key, value in obj.items()
        }


class DictDecoder(Decoder, handler_for=dict):
    def _decode(self, obj_type: type, value: dict) -> Any:
        return {
            Decoder(self.encoded_data, key, self.locator, self)
            .instance: Decoder(self.encoded_data, value, self.locator, self)
            .instance
            for key, value in value.items()
        }
