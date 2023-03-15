from typing import TypeVar

from pypg.type_utils import find_closest_relative

T = TypeVar("T")


class TypeRegistry(dict[type, T]):
    def find_closest_relative(self, t, constraining_base: type | None = None):
        types_to_compare = (
            (t_i for t_i in self if issubclass(t_i, constraining_base))
            if constraining_base is not None
            else self
        )
        return find_closest_relative(t, *types_to_compare)

    def __getitem__(self, item) -> T:
        if isinstance(item, slice):
            try:
                return self[self.find_closest_relative(item.start, item.stop)]
            except (ValueError, AttributeError, KeyError):
                raise KeyError(f"No related types founnd for {item}")
        else:
            return super().__getitem__(item)
