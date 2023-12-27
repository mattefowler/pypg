from pypg import Property, PropertyClass
from pypg.traits.member_named import MemberNamed


class Named(PropertyClass):
    @classmethod
    def name_traits(cls):
        return ()

    name = Property[str](traits=[name_traits])

    @classmethod
    def intrinsic_traits(cls):
        return (MemberNamed(),)
