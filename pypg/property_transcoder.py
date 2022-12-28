from typing import Any

from pypg import PropertyClass
from pypg.transcode import Decoder, Encoder


class PropertyClassEncoder(Encoder, handler_for=PropertyClass):
    def _encode(self, obj: PropertyClass):
        return {
            p.name: Encoder(p.get(obj), self).obj_id
            for p in type(obj).properties
        }


class PropertyClassDecoder(Decoder, handler_for=PropertyClass):
    def _decode(self, obj_type: type, property_values: dict[str, Any]) -> Any:
        return obj_type(
            **{
                name: Decoder(
                    self.encoded_data, attr, self.locator, self
                ).instance
                for name, attr in property_values.items()
            }
        )
