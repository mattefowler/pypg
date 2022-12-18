from typing import Any

from pyproperty import PropertyClass
from pyproperty.transcode import Decoder, Encoder


class PropertyClassEncoder(Encoder, handled_types=PropertyClass):
    @classmethod
    def _encode(cls, obj_type: type[PropertyClass], obj: PropertyClass):
        return {
            p.name: Encoder.encode(p.get(obj)) for p in obj_type.properties
        }


class PropertyClassDecoder(Decoder, handled_types=PropertyClass):
    @classmethod
    def _decode(cls, obj_type: type, property_values: dict[str, Any]) -> Any:
        return obj_type(
            **{name: Decoder.decode(attr) for name, attr in property_values}
        )
