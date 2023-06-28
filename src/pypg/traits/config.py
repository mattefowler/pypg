import json

from pypg import Encoder, encode, MetadataTrait
from pypg.property import PropertyClass, Property, PropertyType
from pypg.property_transcoder import PropertyClassEncoder


class ConfigEncoder(PropertyClassEncoder):
    def _encode(self, obj: PropertyClass):
        return {
            p.name: Encoder(p.get(obj), self, self.overrides).obj_data
            for p in filter(Config.has_config_data, type(obj).properties)
        }


class Config(MetadataTrait):
    def __init__(self, include=True):
        super().__init__(include)

    @classmethod
    def encode(cls, obj):
        return encode(obj, overrides={PropertyClass: ConfigEncoder})

    @classmethod
    def has_config_data(cls, p: Property):
        for pt in p.traits:
            if isinstance(pt, Config):
                return pt.value
        if issubclass(type(p.value_type), PropertyType):
            p_val_type: PropertyType = p.value_type
            return any(filter(cls.has_config_data, p_val_type.properties))

    @classmethod
    def to_file(cls, obj, path: str):
        with open(path, 'w') as file:
            json.dump(cls.encode(obj), file)

    @classmethod
    def to_string(cls, obj) -> str:
        return json.dumps(cls.encode(obj))
