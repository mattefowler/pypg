from __future__ import annotations

__all__ = [
    "FunctionReference",
    "Factory",
    "MethodReference",
    "PostGet",
    "PostSet",
    "PreSet",
    "Property",
    "PropertyType",
    "PropertyClass",
    "Trait",
]

import itertools
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any, Callable, Generic, Iterable, Protocol, TypeVar

T = TypeVar("T")


class PropertyType(type):
    def __init__(cls, name: str, bases: tuple[type], attrs: dict[str, Any]):
        super().__init__(name, bases, attrs)
        properties = []
        for name, value in attrs.items():
            if isinstance(value, Property):
                value.__bind__(name, cls)
                properties.append(value)
        cls.__properties = tuple(properties)
        for p in cls.properties:
            p.__bind_subclass__(cls)
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
        p.__init_instance__(self._instance, value)
        self._uninitialized.remove(p)

    @classmethod
    def for_instance(cls, instance: PropertyClass) -> _InitializationContext:
        return cls._active[instance]

    def initialize(self):
        while self._uninitialized:
            p = self._uninitialized[0]
            self.init_property(p)


class Factory(Protocol[T]):
    def __call__(self, instance: PropertyClass, *args, **kwargs) -> T:
        pass


class FunctionReference(Generic[T]):
    def __init__(self, func: Protocol[T], *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def _get_call_params(self, args, kwargs):
        if args:
            args = (*args, self._args)
        else:
            args = self._args

        if kwargs:
            kw = self._kwargs.copy()
            kw.update(kwargs)
            kwargs = kw
        else:
            kwargs = self._kwargs
        return args, kwargs

    def __call__(self, *args, **kwargs) -> T:
        args, kwargs = self._get_call_params(args, kwargs)
        return self._func(*args, **kwargs)


class MethodReference(FunctionReference[T]):
    def __call__(self, instance: PropertyClass, *args, **kwargs) -> T:
        bound = getattr(instance, self._func.__name__)
        args, kwargs = self._get_call_params(args, kwargs)
        return bound(*args, **kwargs)


class Trait:
    def __init__(self, subject: Property = None):
        self.subject = subject

    def __bind__(self, subject: Property):
        self.subject = subject

    def __init_instance__(self, instance: PropertyClass):
        pass


class DataModifier(Trait, ABC):
    @abstractmethod
    def apply(self, instance, value) -> Any:
        """Perform the required modification of the data and return the result."""


class PostGet(DataModifier, ABC):
    pass


class PreSet(DataModifier, ABC):
    pass


class PostSet(DataModifier, ABC):
    pass


DEFAULT_TYPES = FunctionReference[Factory] | T | None


class Getter(Protocol):
    def __call__(self, instance: PropertyClass) -> T:
        """Return an instance attribute."""


class Setter(Protocol):
    def __call__(self, instance: PropertyClass, value: T) -> Any:
        """Assign a value to an attribute of an instance. Any return value
        will be ignored."""


class _PropertyMeta(type):
    def __instancecheck__(cls, instance):
        if isinstance(instance, Property._Proxy):
            instance = instance._property
        return super().__instancecheck__(instance)


TraitProvider = Trait | classmethod


class Property(Generic[T], metaclass=_PropertyMeta):
    def __init__(
        self,
        default: DEFAULT_TYPES = None,
        getter: Getter[T] = None,
        setter: Setter[T] = None,
        traits: TraitProvider | Iterable[TraitProvider] = (),
    ):
        super().__init__()
        self._subclass_proxies: dict[PropertyType, Property._Proxy] = {}
        self._default = default
        self.name = None
        self.__declaring_type = None
        self._getter = self.default_getter if getter is None else getter
        self._setter = self.default_setter if setter is None else setter
        self.__traits = tuple(
            filter(None, traits if isinstance(traits, Iterable) else [traits])
        )

    @cached_property
    def value_type(self):
        return self.__orig_class__.__args__[0]

    def __bind__(self, name, cls: PropertyType):
        self.name = name
        self.__declaring_type = cls

    def __bind_subclass__(self, cls):
        proxy = self._Proxy(self, cls)
        for t in proxy.traits:
            t.__bind__(self)
        self._subclass_proxies[cls] = proxy

    def __init_instance__(self, instance: PropertyClass, value):
        proxy = self._subclass_proxies[type(instance)]
        proxy.__init_instance__(instance, value)

    def create_default_value(self, instance):
        return (
            self._default(instance)
            if isinstance(self._default, (FunctionReference, Callable))
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
        proxy = self._subclass_proxies[owner]
        return proxy if instance is None else proxy.get(instance)

    def __set__(self, instance, value):
        self._subclass_proxies[type(instance)].set(instance, value)

    def get(self, instance):
        return getattr(instance, self.name)

    def set(self, instance, value):
        return setattr(instance, self.name, value)

    @property
    def traits(self):
        return self.__traits

    class _Proxy:
        def __init__(self, p: Property, owner: PropertyClass):
            self._property = p
            self.__owner = owner
            self.__traits = tuple(
                itertools.chain.from_iterable(
                    map(self.__get_traits, self._property.traits)
                )
            )
            self.__post_get = tuple(
                t for t in self.__traits if isinstance(t, PostGet)
            )
            self.__pre_set = tuple(
                t for t in self.__traits if isinstance(t, PreSet)
            )
            self.__post_set = tuple(
                t for t in self.__traits if isinstance(t, PostSet)
            )

        def __getattr__(self, item):
            return getattr(self._property, item)

        def __get_traits(
            self, trait_provider: Trait | classmethod
        ) -> Iterable[Trait]:
            if isinstance(trait_provider, Trait):
                yield trait_provider
            else:
                result = getattr(self.__owner, trait_provider.__name__)()
                if result is None:
                    return
                if isinstance(result, Trait):
                    yield result
                else:
                    yield from result

        def get(self, instance):
            result = self._property._getter(instance)
            for t in self.__post_get:
                result = t.apply(instance, result)
            return result

        def set(self, instance, value):
            for t in self.__pre_set:
                value = t.apply(instance, value)
            self._property._setter(instance, value)
            for t in self.__post_set:
                t.apply(instance, value)

        def __init_instance__(self, instance, value):
            for t in self.traits:
                t.__init_instance__(instance)
            self.set(instance, value)

        @property
        def traits(self):
            return self.__traits


class PropertyClass(metaclass=PropertyType):
    def __init__(self, **config):
        super().__init__(**config)
