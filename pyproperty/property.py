from __future__ import annotations

from functools import cached_property
from typing import Any, Callable, Generic, Iterable, Protocol, TypeVar

T = TypeVar("T")


class Property:
    pass


class PropertyType(type):
    def __init__(cls, name: str, bases: tuple[type], attrs: dict[str, Any]):
        super().__init__(name, bases, attrs)
        properties = []
        for name, value in attrs.items():
            if isinstance(value, Property):
                value.__bind__(name, cls)
                properties.append(value)
        cls.__properties = tuple(properties)
        cls.__create_initializer(cls)

    @property
    def properties(cls) -> Iterable[Property]:
        yield from cls.__properties
        for b in cls.__bases__:
            if isinstance(b, PropertyType):
                yield from b.properties

    @classmethod
    def __create_initializer(mcs, cls: PropertyType):
        cls_init = cls.__init__

        def initializer(instance: PropertyClass, *args, **property_values):
            with _InitializationContext(
                instance, **property_values
            ) as init_ctx:
                init_ctx.initialize()
                cls_init(instance, *args, **init_ctx.config)

        cls.__init__ = initializer


class _InitMeta(type):
    _active: dict[PropertyClass, _InitializationContext] = {}

    def __call__(cls, instance, **property_values):
        try:
            return cls._active[instance]
        except KeyError:
            ctx = cls.__new__(cls, instance, **property_values)
            ctx.__init__(instance, **property_values)
            cls._active[instance] = ctx
            return ctx


class _InitializationContext(metaclass=_InitMeta):
    def __init__(
        self, instance: PropertyClass, **property_values: dict[str, Any]
    ):
        self._instance = instance
        self.config = property_values
        self._uninitialized = [*type(instance).properties]
        self.__entry_count = 0

    def __enter__(self):
        if not self.__entry_count:
            type(self)._active[self._instance] = self
        self.__entry_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__entry_count -= 1
        if not self.__entry_count:
            type(self)._active.pop(self._instance)

    def init_property(self, p: Property):
        try:
            value = self.config.pop(p.name)
        except KeyError:
            value = p.create_default_value(self._instance)
        setattr(self._instance, p.name, value)
        self._uninitialized.remove(p)

    @classmethod
    def for_instance(cls, instance: PropertyClass) -> _InitializationContext:
        return cls._active[instance]

    def initialize(self):
        while self._uninitialized:
            p = self._uninitialized[0]
            self.init_property(p)


class PropertyClass(metaclass=PropertyType):
    def __init__(self, **config):
        super().__init__(**config)


class FactoryMethod(Protocol[T]):
    def __call__(self, instance: PropertyClass, *args, **kwargs) -> T:
        pass


class DefaultFactory(Generic[T]):
    def __init__(self, factory: FactoryMethod[T], *args, **kwargs):
        self._factory = factory
        self._args = args
        self._kwargs = kwargs

    def __call__(self, instance) -> T:
        return self._factory(instance, *self._args, **self._kwargs)


class InstanceMethodDefault(DefaultFactory[T]):
    def __call__(self, instance: PropertyClass) -> T:
        factory = getattr(instance, self._factory.__name__)
        return factory(*self._args, **self._kwargs)


class ClassMethodDefault(DefaultFactory[T]):
    def __call__(self, instance: PropertyClass) -> T:
        factory = getattr(type(instance), self._factory.__name__)
        return factory(*self._args, **self._kwargs)


class PropertyTrait:
    pass


DEFAULT_TYPES = DefaultFactory | FactoryMethod | T | None


class Getter(Protocol):
    def __call__(self, instance: PropertyClass) -> T:
        """Return an instance attribute."""


class Setter(Protocol):
    def __call__(self, instance: PropertyClass, value: T) -> Any:
        """Assign a value to an attribute of an instance. Any return value
        will be ignored."""


def overridable(accessor: Getter | Setter):
    def __call__(instance, *args, **kwargs):
        return getattr(instance, accessor.__name__)(*args, **kwargs)

    return __call__


class Property(Generic[T]):
    def __init__(
        self,
        default: DEFAULT_TYPES = None,
        getter: Getter[T] = None,
        setter: Setter[T] = None,
    ):
        super().__init__()
        self._default = default
        self.name = None
        self.__declaring_type = None
        self._getter = self.default_getter if getter is None else getter
        self._setter = self.default_setter if setter is None else setter

    @cached_property
    def value_type(self):
        return self.__orig_class__.__args__[0]

    def __bind__(self, name, cls: PropertyType):
        self.name = name
        if self.__declaring_type is None:
            self.__declaring_type = cls
        self.__bind_subclass__(cls)

    def __bind_subclass__(self, cls):
        pass

    def create_default_value(self, instance):
        return (
            self._default(instance)
            if isinstance(self._default, (DefaultFactory, Callable))
            else self._default
        )

    def default_getter(self, instance):
        try:
            return instance.__dict__[self]
        except KeyError as k:
            init_ctx = None
            try:
                init_ctx = _InitializationContext.for_instance(instance)
            except KeyError:
                pass
            if init_ctx is None:
                raise
            init_ctx.init_property(self)
            return self.default_getter(instance)

    def default_setter(self, instance, value):
        instance.__dict__[self] = value

    def __get__(self, instance: PropertyClass, owner: PropertyType):
        if instance is None:
            return self

        return self._getter(instance)

    def __set__(self, instance, value):
        self._setter(instance, value)

    def get(self, instance):
        return getattr(instance, self.name)

    def set(self, instance, value):
        return setattr(instance, self.name, value)
