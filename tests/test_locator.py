from unittest import TestCase

from pypg import Locator, allow_subclass, strict
from pypg import get_fully_qualified_name


class Foo:
    pass


class Bar(Foo):
    pass


class TestLocator(TestCase):
    def test_locator(self):
        locator = Locator()
        self.assertIs(Foo, locator(get_fully_qualified_name(Foo)))

    def test_strict(self):
        locator = Locator(Foo, load_policy=strict)
        self.assertIs(Foo, locator(get_fully_qualified_name(Foo)))
        bar_fqn = get_fully_qualified_name(Bar)
        with self.assertRaises(PermissionError):
            locator(bar_fqn)
        locator.allow(Bar)
        self.assertIs(Bar, locator(bar_fqn))

    def test_subclass(self):
        locator = Locator(Foo, load_policy=allow_subclass)
        self.assertIs(Foo, locator(get_fully_qualified_name(Foo)))
        self.assertIs(Bar, locator(get_fully_qualified_name(Bar)))

    def test_not_found(self):
        with self.assertRaises(TypeError):
            Locator()("asdf")

    def test_none(self):
        self.assertIs(type(None), Locator()(get_fully_qualified_name(type(None))))
