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
import typing
from collections.abc import Collection, Iterable, Callable
from datetime import datetime
from enum import Enum
from types import FunctionType, GenericAlias, MethodType, NoneType
from typing import Any, Self, Union, _GenericAlias

from pypg.locator import Locator
from pypg.type_registry import TypeRegistry
from pypg.type_utils import get_fully_qualified_name

primitives = (str, int, float, bool, NoneType)
Serializable = dict | list | Union[primitives]

default_locator = Locator()


class _Transcoder:
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

    @classmethod
    def _resolve_handler(cls, obj_type, overrides: dict[type, type[Self]]):
        if overrides:
            try:
                return TypeRegistry(overrides)[obj_type:]
            except KeyError:
                pass
        return cls[obj_type]


class MonotonicID:
    def __init__(self):
        self.objects: dict[object, int] = {}

    def __call__(self, obj: object) -> int:
        try:
            return self.objects[id(obj)]
        except KeyError:
            self.objects[id(obj)] = (objid := len(self.objects))
            return objid


class Encoder(_Transcoder):
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
        cls,
        obj,
        parent: Encoder | None,
        overrides: dict[type, type[Encoder]] = None,
        id_provider: Callable[[object], int | str] = None,
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
        return super().__new__(encoder_type)

    def __init__(
        self,
        obj,
        parent: Encoder | None,
        overrides: dict[type, type[Encoder]],
        id_provider: Callable[[object], int | str] = None,
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
            self.data: dict[int, str | list[str, Any]] = {}
            self.get_id = MonotonicID() if id_provider is None else id_provider
        else:
            self.data = parent.data
            self.get_id = parent.get_id
        self._obj_id = self.get_id(obj)
        self.obj_data = self._pack(obj)
        if parent is None:
            self.data[self._obj_id] = self.obj_id

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

    def _pack(self, obj) -> list[str, int, Any]:
        obj_type = self._get_obj_type(obj)
        if self.obj_id in self.data:
            return Encoder(
                _ObjectReference(obj), self, self.overrides
            ).obj_data
        encoded_data = [
            get_fully_qualified_name(obj_type),
            (self._encode(obj), self.obj_id),
        ]
        self.data[self.obj_id] = encoded_data
        return encoded_data

    def _encode(self, obj):
        return obj


class PrimitiveEncoder(Encoder, handler_for=primitives):
    def _pack(self, obj) -> list[str, int, Any]:
        obj_type = self._get_obj_type(obj)
        return [
            get_fully_qualified_name(obj_type),
            self._encode(obj),
        ]


class Decoder(_Transcoder, handler_for=primitives):
    """
    Decoders transform encoded data into instances equivalent to the originally
    encoded object.
    """

    def __new__(
        cls,
        encoded_data: dict,
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
        # if obj_id is None:
        #     obj_id = encoded_data[cls.root_key]
        attr_type, *_ = cls._unpack(encoded_data, locator)
        decoder_cls = cls._resolve_handler(attr_type, overrides)
        return super().__new__(decoder_cls)

    def __init__(
        self,
        encoded_data: dict | list,
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
        self.locator = locator
        self.instance = self.decode()

    def decode(self) -> Any:
        member_type, (member_data, obj_id) = self._unpack(
            self.encoded_data, self.locator
        )
        try:
            return self.decoded_objects[obj_id]
        except KeyError:
            pass
        instance = self._decode(member_type, member_data)
        self.decoded_objects[obj_id] = instance
        return instance

    @classmethod
    def _unpack(
        cls,
        encoded_data: dict[str, list[str, Any]],
        locator: Locator,
    ) -> tuple[type, Any]:
        fully_qualified_name, obj_data = encoded_data
        try:
            t = locator(fully_qualified_name)
        except TypeError:
            if fully_qualified_name != NoneType.__name__:
                raise
            t = NoneType
        return t, obj_data

    def _decode(self, obj_type: type, value: Any) -> Any:
        return obj_type(value)


class PrimitiveDecoder(Decoder, handler_for=primitives):
    def decode(self) -> Any:
        member_type, value = self._unpack(self.encoded_data, self.locator)
        return self._decode(member_type, value)


class _ObjectReference:
    def __init__(self, obj: Any):
        while isinstance(obj, _ObjectReference):
            obj = obj.obj
        self.obj = obj


class _ObjectReferenceEncoder(Encoder, handler_for=_ObjectReference):
    def _encode(self, obj_ref):
        return self.get_id(obj_ref.obj)


class _ObjectReferenceDecoder(Decoder, handler_for=_ObjectReference):
    def _decode(self, obj_type: type, value: Any) -> Any:
        return self.decoded_objects[value]


class NoneTypeDecoder(PrimitiveDecoder, handler_for=NoneType):
    def _decode(self, obj_type: type, value: Any) -> Any:
        return None


def encode(obj, overrides: dict[type, type[Encoder]] = None, id_provider: Callable[[object], int | str] = None) -> Any:
    """
    A convenience function to simplify the syntax of using an Encoder to
    transform an object's data into a JSON-serializable format.
    Args:
        obj: the object to be serialized.
        overrides: encoders for specific types to use in place of previously registered handlers.
        id_provider: an optional function used to produce IDs for each serialized object.

    Returns:
        transformed-data of obj
    """
    return Encoder(obj, None, overrides, id_provider).obj_data


def to_string(obj, overrides: dict[type, type[Encoder]] | None = None, id_provider: Callable[[object], int | str] = None) -> str:
    """
    A convenience function to simplify using an Encoder to transform an
    object's data into a JSON-parseable string.
    Args:
        obj: the object to be stringified.
        overrides: encoders for specific types to use in place of previously registered handlers.
        id_provider: an optional callable that returns a function used to produce IDs for each serialized object.

    Returns:
        a JSON-parseable string of the object's data.
    """
    return json.dumps(encode(obj, overrides, id_provider))


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
        locator: an optional object used to retrieve runtime-types from serialized representations.
        overrides: encoders for specific types to use in place of previously registered handlers.

    Returns:
        a JSON-parseable string of the object's data.
    """
    return decode(
        json.loads(encoded_object), locator=locator, overrides=overrides
    )


def to_file(
    obj, path: str, overrides: dict[type, type[Encoder]] | None = None
):
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
        obj_data, locator=locator, parent=None, overrides=overrides
    ).instance


class TypeEncoder(PrimitiveEncoder, handler_for=(type, FunctionType)):
    def _encode(self, obj_type):
        return get_fully_qualified_name(obj_type)


class TypeDecoder(PrimitiveDecoder, handler_for=(type, FunctionType)):
    def _decode(self, _, fully_qualified_name: str):
        return self.locator(fully_qualified_name)


class GenericEncoder(TypeEncoder, handler_for=(GenericAlias, _GenericAlias)):
    @classmethod
    def _get_obj_type(cls, obj):
        return type

    def _encode(self, obj_type):
        return f"{get_fully_qualified_name(obj_type)}[{','.join(map(get_fully_qualified_name, typing.get_args(obj_type)))}]"


class CollectionEncoder(Encoder, handler_for=(tuple, set, list)):
    def _encode(self, obj: Collection):
        return [Encoder(item, self, self.overrides).obj_data for item in obj]


class CollectionDecoder(Decoder, handler_for=(tuple, set, list)):
    def _decode(self, obj_type, obj_data: Collection[Any]):
        return obj_type(
            (
                Decoder(
                    encoded_obj_data,
                    self.locator,
                    self,
                    overrides=self.overrides,
                ).instance
                for encoded_obj_data in obj_data
            )
        )


class DictEncoder(Encoder, handler_for=dict):
    def _encode(self, obj: dict):
        return [
            *zip(
                *(
                    (
                        Encoder(obj, self, self.overrides).obj_data
                        for obj in item
                    )
                    for item in obj.items()
                )
            )
        ]


class DictDecoder(Decoder, handler_for=dict):
    def _decode(self, obj_type: type, items: list[list, list]) -> Any:
        return (
            {
                Decoder(key, self.locator, self, overrides=self.overrides)
                .instance: Decoder(
                    item, self.locator, self, overrides=self.overrides
                )
                .instance
                for key, item in zip(*items)
            }
            if items
            else {}
        )


class EnumEncoder(Encoder, handler_for=Enum):
    def _encode(self, obj: Enum):
        return obj.name


class EnumDecoder(Decoder, handler_for=Enum):
    def _decode(self, obj_type: type[Enum], value: str) -> Any:
        return obj_type[value]


class MethodEncoder(Encoder, handler_for=MethodType):
    def _encode(self, bound: MethodType):
        return [
            Encoder(bound.__self__, self, self.overrides).obj_data,
            bound.__func__.__name__,
        ]


class MethodDecoder(Decoder, handler_for=MethodType):
    def _decode(self, obj_type: type, value: tuple[list, str]) -> Any:
        instance_data, func_name = value
        instance = Decoder(
            instance_data, self.locator, self, self.overrides
        ).instance
        return getattr(instance, func_name)


class DateTimeEncoder(Encoder, handler_for=datetime):
    def _encode(self, obj: datetime):
        return obj.timestamp()


class DateTimeDecoder(Decoder, handler_for=datetime):
    def _decode(self, obj_type: datetime, value: Any) -> Any:
        return datetime.fromtimestamp(value)
