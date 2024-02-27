from __future__ import annotations

import itertools
from abc import ABC, abstractmethod, ABCMeta
from functools import cached_property, wraps
from types import FunctionType
from typing import Any, Callable, Generic, Iterable, Protocol, TypeVar

from pypg.type_utils import get_fully_qualified_name

T = TypeVar("T")


class PropertyType(ABCMeta):
    """
    Metaclass for types using Properties. All PropertyTypes have an __init__
    generated that accepts keyword-arguments matching the names of the
    Properties declared by the type.
    """

    def __new__(mcs, name: str, bases: tuple[type], attrs: dict[str, Any]):
        properties = [
            p for p in attrs.values() if isinstance(p, Property)
        ]
        for b in bases:
            if issubclass(type(b), PropertyType):
                for p in b.properties:
                    if p not in properties:
                        properties.append(p)

        cls = super().__new__(
            mcs,
            name,
            bases,
            {**attrs, "properties": properties},
        )
        for p in cls.properties:
            p.__bind_subclass__(cls)
        cls.__create_initializer(cls)
        return cls

    properties: tuple[Property, ...]

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

    def intrinsic_traits(cls) -> Iterable[Trait]:
        return ()


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
    def __call__(
        self, instance: PropertyClass, *args, **kwargs
    ) -> T:  # pragma: no cover
        pass


class FunctionReference(Generic[T]):
    def __init__(self, func: Protocol[T], *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def _get_call_params(self, args, kwargs):
        if args:
            args = (*args, *self._args)
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
    """
    A Trait is a decorator-like class that extends Property metadata and
    behaviors.
    """

    def __init__(self):
        """
        Creates a new Trait instance.
        """
        self.subject: Property = None

    def __bind__(self, subject: Property):
        """
        Called during type-construction to associate a Trait with a Property.
        """
        self.subject = subject

    def __init_instance__(self, instance: PropertyClass, attr: Any):
        """
        Allows a Trait to participate in construction of each instance of the
        class and attribute that it is a part of.
        Args:
            instance: the instance under construction.
        """


class DataModifier(Trait, ABC):
    """
    A Datamodifier participates in data-access. It may alter the value being
    stored or returned, or trigger side-effects.
    """

    @abstractmethod
    def apply(self, instance: PropertyClass, value) -> Any:
        """
        Perform the required modification of the data and return the result.
        Args:
            instance: the object instance whose Property is being accessed.
            value: the value of the trait's subject Property.

        Returns:
            DataModifiers must return a value, regardless of if it was changed
            or not.
        """


class PostGet(DataModifier, ABC):
    """
    PostGet's apply method is triggered after its subject's getter method has
    executed.
    """


class PreSet(DataModifier, ABC):
    """
    PreSet's apply method is triggered prior to its subject's setter method.
    """


class PostSet(DataModifier, ABC):
    """
    PostSet's apply method is triggered after its subject's setter method has
    executed.
    """


class DataModifierMixin(DataModifier, ABC):
    def __class_getitem__(
        cls, modifiers: type[DataModifier] | Iterable[DataModifier]
    ):
        """
        Parameterizes a DataModifier Trait class with one or more data-access
        actions.
        Args:
            *modifiers: the dataaccessmodifier

        Returns:

        """
        if not isinstance(modifiers, Iterable):
            modifiers = (modifiers,)
        return type(
            cls.__name__,
            (cls, *modifiers),
            {
                cls.modifier_triggers.fget.__name__: modifiers,
                "__module__": cls.__module__,
            },
        )

    @property
    @abstractmethod
    def modifier_triggers(self) -> tuple[type[DataModifier]]:
        """Returns the DataModifier types implemented."""


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
        if isinstance(instance, _Proxy):
            instance = instance._property
        return super().__instancecheck__(instance)

    def __subclasscheck__(cls, subclass):
        return issubclass(_Proxy, subclass) or super().__subclasscheck__(
            subclass
        )


TraitProvider = Trait | classmethod


def is_method(cls: type, obj: Any) -> bool:
    return (
        isinstance(obj, (FunctionType, classmethod, staticmethod))
        and obj in cls.__dict__.values()
    )


class Property(Generic[T], metaclass=_PropertyMeta):
    """
    Property is a descriptor class used for instance-data storage as well as
    declaring metadata and behaviors triggered by data-access.
    """

    def __init__(
        self,
        default: DEFAULT_TYPES = None,
        getter: Getter[T] = None,
        setter: Setter[T] = None,
        traits: TraitProvider | Iterable[TraitProvider] = (),
    ):
        """
        Construct a new Property attribute of a class. A Property will only
        function as intended in classes deriving from PropertyClass or that use
        the PropertyType metaclass.
        Args:
            default: used when a value for this Property is not provided at
                construction time. Default may be a literal or callable object
                accepting the instance under construction that returns the
                composing instance's value for this Property. Default factories
                may be a classmethod or an instance method, and any method
                overrides will be used regardless of where in the type
                hierarchy the Property is declared.
            getter: a callable object used to handle the get-semantics for the
                Property.
            setter: a callable object used to handle the set-semantics for the
                Property.
            traits: a collection of Trait instances, or classmethods returning
                them, that apply to this Property. Traits are collected and
                applied in a context-specific manner such that the traits of a
                Property provided by a classmethod may be overridden by a
                subclass of the type originally declaring the Property.
        """
        super().__init__()
        self._subclass_proxies: dict[PropertyType, _Proxy] = {}
        self._default = default
        self.name = None
        self.__declaring_type: PropertyType = None
        self._getter = self.default_getter if getter is None else getter
        self._setter = self.default_setter if setter is None else setter
        self.__traits = tuple(
            filter(None, traits if isinstance(traits, Iterable) else [traits]),
        )

    @property
    def declaring_type(self):
        return self.__declaring_type

    @cached_property
    def value_type(self):
        return self.__orig_class__.__args__[0]

    def __set_name__(self, owner, name):
        self.name = name
        self.__declaring_type = owner
        for t in self.traits:
            try:
                t.__bind__(self)
            except AttributeError:
                pass

    @property
    def declaring_type(self) -> PropertyType:
        return self.__declaring_type

    def __bind_subclass__(self, cls):
        self._subclass_proxies[cls] = _Proxy(self, cls)

    def __init_instance__(self, instance: PropertyClass, value):
        """
        Allows a Property and its Traits to participate in instance
        construction.
        Args:
            instance: the instance being constructed.
            value: the value of this Property to be assigned to instance.
        """
        proxy = self._subclass_proxies[type(instance)]
        proxy.__init_instance__(instance, value)

    def create_default_value(self, instance) -> T:
        """
        Return the value used in construction of instance if no keyword
        argument matching self's name is provided.
        Args:
            instance: the instance whose default value of self is returned.
        Returns:
            a default of this property for the instance provided.
        """
        return (
            self._default(instance)
            if isinstance(self._default, (FunctionReference, Callable))
            else self._default
        )

    @cached_property
    def attribute_key(self):
        return f"#_{self.__declaring_type.__name__}__{self.name}"

    def default_getter(self, instance) -> T:
        """
        The getter method used by a Property if none is otherwise provided. It
        retrieves its data in instance.__dict__ using self as the key. If
        instance is under construction, the initialization process will
        construct it on-demand as required.
        Args:
            instance: the instance storing the data for self.
        Returns:
            the value of this property for instance.
        """

        try:
            return instance.__dict__[self.attribute_key]
        except KeyError as k:
            init_ctx = None
            try:
                init_ctx = _InitializationContext.for_instance(instance)
            except KeyError as k:
                pass
            if init_ctx is None:
                raise AttributeError(
                    f"object {instance} as no property {self}",
                    obj=instance,
                    name=self.name,
                )
            init_ctx.init_property(self)
            return self.default_getter(instance)

    def default_setter(self, instance, value):
        """
        The setter method used by a Property if none is otherwise provided. It
        stores its data in instance.__dict__ using self as the key.
        Args:
            instance: the instance whose Property value is being set.
            value: the value to be stored for instance.
        """
        instance.__dict__[self.attribute_key] = value

    def __get__(self, instance: PropertyClass, owner: PropertyType):
        proxy = self._subclass_proxies[owner]
        return proxy if instance is None else proxy.__get__(instance, owner)

    def __set__(self, instance, value):
        self._subclass_proxies[type(instance)].__set__(instance, value)

    def get(self, instance) -> T:
        """
        Convenience method to use Property get-semantics functionally.
        Args:
            instance: the instance whose data is retrieved.

        Returns:
            Instance's value of this Property.
        """
        return getattr(instance, self.name)

    def set(self, instance, value):
        """
            Convenience method to use Property set-semantics functionally.
        Args:
            instance: the instance whose data is assigned.
            value: the value to be assigned to this instance and Property.
        """
        return setattr(instance, self.name, value)

    @property
    def traits(self):
        """
        Returns: The Traits of this Property.
        """
        return self.__traits

    def __lt__(self, other):
        """implemented to support entities that assume dict-keys are sortable."""
        return self.name < other

    def __str__(self):
        return f"{get_fully_qualified_name(self.__declaring_type)}.{self.name}"


class _Proxy:
    """
    _Proxy wraps a Property to provide subclass-specific Traits, allowing
    derived types to modify the behaviors and metadata of base-class Properties
    """

    __qualname__ = Property.__qualname__
    __name__ = Property.__name__

    def __init__(self, p: Property, owner: type[PropertyClass]):
        self._property = p
        self.__owner = owner
        self.__traits = tuple(
            itertools.chain.from_iterable(
                map(self.__get_traits, self._property.traits),
            )
        )

        self.__post_get = tuple(
            t for t in self.traits if isinstance(t, PostGet)
        )
        self.__pre_set = tuple(
            t for t in self.traits if isinstance(t, PreSet)
        )
        self.__post_set = tuple(
            t for t in self.traits if isinstance(t, PostSet)
        )
        for t in self.traits:
            t.__bind__(p)

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

    @wraps(Property.get)
    def __get__(self, instance, owner):
        result = self._property._getter(instance)
        for t in self.__post_get:
            result = t.apply(instance, result)
        return result

    @wraps(Property.set)
    def __set__(self, instance, value):
        for t in self.__pre_set:
            value = t.apply(instance, value)
        self._property._setter(instance, value)
        for t in self.__post_set:
            t.apply(instance, value)

    @wraps(Property.__init_instance__)
    def __init_instance__(self, instance, value):
        for t in self.traits:
            t.__init_instance__(instance, value)
        self.set(instance, value)

    @cached_property
    def _value_type_traits(self):
        return (
            self.value_type.intrinsic_traits()
            if issubclass(type(self._property.value_type), PropertyType)
            else ()
        )

    @property
    @wraps(Property.traits.fget)
    def traits(self):
        return tuple((*self.__traits, *self._value_type_traits))

    def __str__(self):
        return (
            f"{get_fully_qualified_name(self.__owner)}.{self._property.name}"
        )


def __get_obj_init_error():
    try:
        object(0)
    except TypeError as te:
        return str(te)
    raise TypeError("Expected error not raised")


_object_init_error = __get_obj_init_error()


class PropertyClass(metaclass=PropertyType):
    """
    PropertyClass is a convenience base class for classes using Properties. All
    PropertyTypes have an __init__ generated that accepts keyword-arguments
    matching the names of the Properties declared by the type.
    """

    def __init__(self, **config):
        try:
            super().__init__(**config)
        except TypeError as te:
            if str(te) == _object_init_error:
                raise TypeError(
                    f"received unexpected keyword arguments: {config}"
                ) from te
