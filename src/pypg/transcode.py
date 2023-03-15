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
from types import NoneType
from typing import Any, Union, Self

from pypg.locator import Locator
from pypg.type_registry import TypeRegistry
from pypg.type_utils import get_fully_qualified_name

primitives = (str, int, float, bool, NoneType)
Serializable = dict | list | Union[primitives]

default_locator = Locator()


class _Transcoder:
    root_key = "root"

    _registry: TypeRegistry[_Transcoder] = None

    def __init_subclass__(cls, handler_for: type | Iterable[type] = (), **kwargs):
        if isinstance(handler_for, type):
            handler_for = (handler_for,)
        if cls._registry is None:
            cls._registry = TypeRegistry()
        cls._registry.update({t: cls for t in handler_for})

    @classmethod
    def __class_getitem__(cls, obj_type: type) -> type[_Transcoder]:
        return cls._registry[obj_type:]

    @classmethod
    def _resolve_handler(cls, obj_type, overrides: dict[type, type[Self]]):
        if overrides:
            try:
                return TypeRegistry(overrides)[obj_type:]
            except KeyError:
                pass
        return cls[obj_type]


class Encoder(_Transcoder, handler_for=primitives):
    """
    Encoders transform python objects into JSON-compliant data-structures for
    storage or transmission. All constituent object data is stored in a flat
    dict keyed by each object's id. The values of the data-dict are lists of
    two elements: the first node contains the fully-qualified type name of the
    object's type, and the second contains a serializable representation of its
    members. The one exception to this pattern is the 'root' node, which
    contains only the address of the object initially passed to the Encoder.
    Subclasses of Encoder transform data for specific types specified by the
    handler_for class-keyword.
    """

    def __new__(
        cls, obj, parent: Encoder | None, overrides: dict[type, type[Encoder]] = None
    ):
        """
        Create a new encoder for the object. If a more-specific encoder-type
        for the object's type exists than the one specific, construct it
        instead.
        Args:
            obj: the object to be encoded.
            parent: the Encoder constructing this one, or None if obj is the
            first object to be encoded.
        """
        encoder_type = cls._resolve_handler(type(obj), overrides)
        if encoder_type is cls:
            return super().__new__(cls)
        else:
            return encoder_type(obj, parent, overrides)

    def __init__(
        self, obj, parent: Encoder | None, overrides: dict[type, type[Encoder]]
    ):
        """
        Initialize a new encoder for the object.
        Args:
            obj: the object to be encoded.
            parent: the Encoder constructing this one, or None if obj is the
            first object to be encoded.
        """
        self.parent = parent
        self.overrides = overrides
        if parent is None:
            self.data: dict[str, str | list[str, Any]] = {}
        else:
            self.data = parent.data
        self._obj_id = self._pack(obj)
        if parent is None:
            self.data[self.root_key] = self.obj_id

    @property
    def obj_id(self) -> str:
        """
        The unique identifier for the object being encoded; this should be a
        string of the id of the object.
        Returns:
            the id of the object passed to this Encoder.
        """
        return self._obj_id

    @classmethod
    def _get_obj_type(cls, obj):
        return type(obj)

    def _pack(self, obj) -> str:
        obj_id = str(id(obj))
        obj_type = self._get_obj_type(obj)
        if obj_id not in self.data:
            encoded_data = [f"{get_fully_qualified_name(obj_type)}"]
            # pack data in 2 stages to prevent infinite recursion when encoding self-referential objects.
            self.data[obj_id] = encoded_data
            encoded_data.append(self._encode(obj))
        return obj_id

    def _encode(self, obj):
        return obj

    @classmethod
    def unpack(cls, data, obj_id=_Transcoder.root_key, locator=default_locator):
        """Transform encoded data into a more readable format, expanding
        objects into container elements instead of referencing by id, and
        duplicating any shared references."""
        if obj_id == _Transcoder.root_key:
            obj_id = data[obj_id]
        obj_type_fqn, obj_data = data[obj_id]
        obj_type = locator(obj_type_fqn)
        e_type = cls[obj_type]
        return [obj_type_fqn, e_type._unpack(data, obj_data, locator)]

    @classmethod
    def _unpack(cls, data, obj_data, locator=default_locator):
        return obj_data


class Decoder(_Transcoder, handler_for=primitives):
    """
    Decoders transform encoded data into instances equivalent to the originally
    encoded object.
    """

    def __new__(
        cls,
        encoded_data: dict,
        obj_id: str | None,
        locator: Locator,
        parent: Decoder | None,
        overrides: dict[type, type[Decoder]] = None,
    ):
        """
        Create a new Decoder. The most appropriate Decoder for the object
        corresponding to obj_id will be resolve and constructed for non-
        primitive data.
        Args:
            encoded_data:
            obj_id:
            locator:
            parent:
        """
        if obj_id is None:
            obj_id = encoded_data[cls.root_key]
        attr_type, attr_data = cls._unpack(encoded_data, obj_id, locator)
        decoder_cls = cls._resolve_handler(attr_type, overrides)
        return (
            super().__new__(cls)
            if decoder_cls is cls
            else decoder_cls(encoded_data, obj_id, locator, parent, overrides=overrides)
        )

    def __init__(
        self,
        encoded_data: dict,
        obj_id: str | None,
        locator: Locator,
        parent: Decoder | None,
        overrides: dict[type, type[Decoder]],
    ):
        self.parent = parent
        self.overrides = overrides
        if parent is None:
            self.decoded_objects = {}
        else:
            self.decoded_objects = parent.decoded_objects
        self.encoded_data = encoded_data
        self.obj_id = obj_id if obj_id is not None else encoded_data[self.root_key]
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
        try:
            t = locator(fully_qualified_name)
        except TypeError:
            if fully_qualified_name != NoneType.__name__:
                raise
            t = NoneType
        return t, value

    def _decode(self, obj_type: type, value: Any) -> Any:
        return obj_type(value)


class NoneTypeDecoder(Decoder, handler_for=NoneType):
    def _decode(self, obj_type: type, value: Any) -> Any:
        return None


def encode(obj, overrides: dict[type, type[Encoder]] = None) -> Any:
    """
    A convenience function to simplify the syntax of using an Encoder to
    transform an object's data into a JSON-serializable format.
    Args:
        obj: the object to be serialized.

    Returns:
        transformed-data of obj
    """
    return Encoder(obj, None, overrides).data


def to_string(obj, overrides: dict[type, type[Encoder]] | None = None) -> str:
    """
    A convenience function to simplify using an Encoder to transform an
    object's data into a JSON-parseable string.
    Args:
        obj: the object to be stringified.

    Returns:
        a JSON-parseable string of the object's data.
    """
    return json.dumps(encode(obj, overrides))


def from_string(
    encoded_object: str,
    locator=default_locator,
    overrides: dict[type, type[Decoder]] | None = None,
) -> Any:
    """
    A convenience function to simplify using an Decoder to transform a string
    of encoded object data into object instances.
    Args:
        obj: the object to be stringified.

    Returns:
        a JSON-parseable string of the object's data.
    """
    return decode(json.loads(encoded_object), locator=locator, overrides=overrides)


def to_file(obj, path: str, overrides: dict[type, type[Encoder]]|None=None):
    with open(path, "w") as f:
        json.dump(encode(obj, overrides=overrides), f)


def from_file(
    path: str,
    locator=default_locator,
    overrides: dict[type, type[Decoder]] | None = None,
):
    with open(path) as f:
        return decode(json.load(f), locator=locator, overrides=overrides)


def decode(
    obj_data,
    locator=default_locator,
    overrides: dict[type, type[Decoder]] | None = None,
):
    return Decoder(
        obj_data, locator=locator, parent=None, obj_id=None, overrides=overrides
    ).instance


def unpack(obj_data, obj_id=Encoder.root_key, locator=default_locator):
    return Encoder.unpack(obj_data, obj_id, locator)


class TypeEncoder(Encoder, handler_for=type):
    def _encode(self, obj_type):
        return get_fully_qualified_name(obj_type)


class TypeDecoder(Decoder, handler_for=type):
    def _decode(self, _, fully_qualified_name: str):
        return self.locator(fully_qualified_name)


class CollectionEncoder(Encoder, handler_for=(tuple, set, list)):
    def _encode(self, obj: Collection):
        return [Encoder(item, self, self.overrides).obj_id for item in obj]

    @classmethod
    def _unpack(cls, data, obj_data: list[str], locator=default_locator):
        return [Encoder.unpack(data, item, locator) for item in obj_data]


class CollectionDecoder(Decoder, handler_for=(tuple, set, list)):
    def _decode(self, obj_type, obj_ids: Collection[str]):
        return obj_type(
            (
                Decoder(
                    self.encoded_data,
                    obj_id,
                    self.locator,
                    self,
                    overrides=self.overrides,
                ).instance
                for obj_id in obj_ids
            )
        )


class DictEncoder(Encoder, handler_for=dict):
    def _encode(self, obj: dict):
        return {
            Encoder(key, self, self.overrides)
            .obj_id: Encoder(value, self, self.overrides)
            .obj_id
            for key, value in obj.items()
        }

    @classmethod
    def _unpack(
        cls,
        data: dict[str, Any],
        obj_data: dict[str, str],
        locator=default_locator,
    ):
        return [
            (
                Encoder.unpack(data, key, locator=locator),
                Encoder.unpack(data, value, locator=locator),
            )
            for key, value in obj_data.items()
        ]


class DictDecoder(Decoder, handler_for=dict):
    def _decode(self, obj_type: type, value: dict) -> Any:
        return {
            Decoder(
                self.encoded_data, key, self.locator, self, overrides=self.overrides
            )
            .instance: Decoder(
                self.encoded_data, value, self.locator, self, overrides=self.overrides
            )
            .instance
            for key, value in value.items()
        }
