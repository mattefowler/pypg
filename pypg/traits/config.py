from pypg import Encoder, encode
from pypg.property import Trait, PropertyClass, Property, PropertyType
from pypg.property_transcoder import PropertyClassEncoder


class ConfigEncoder(PropertyClassEncoder):
    def _encode(self, obj: PropertyClass):
        return {
            p.name: Encoder(p.get(obj), self, self.overrides).obj_id
            for p in filter(Config.has_config_data, type(obj).properties)
        }


class Config(Trait):
    def __init__(self, include=True):
        super().__init__()
        self._include = include

    @classmethod
    def encode(cls, obj):
        return encode(obj, overrides={PropertyClass: ConfigEncoder})

    @classmethod
    def has_config_data(cls, p: Property):
        for pt in p.traits:
            if isinstance(pt, Config):
                return pt._include
        if issubclass(type(p.value_type), PropertyType):
            p_val_type: PropertyType = p.value_type
            return any(filter(cls.has_config_data, p_val_type.properties))
