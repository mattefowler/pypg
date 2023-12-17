from unittest import TestCase

from pypg import TypeRegistry


class Base:
    pass


class A(Base):
    pass


class B(Base):
    pass


class C(Base):
    pass


class DA(A):
    pass


class DB(B):
    pass


class DC(C):
    pass


test_types = (Base, A, B, C, DA, DB, DC)


class TypeRegistryTest(TestCase):
    def test_lookup(self):
        associations = {t: t.__name__ for t in test_types}
        treg = TypeRegistry[str](associations)
        for base, derived in ((A, DA), (B, DB), (C, DC)):
            self.assertIs(treg[base], associations[base])
            self.assertIs(treg[derived], associations[derived])
            self.assertIs(treg[derived:base], associations[derived])
            self.assertIs(treg[derived:], associations[derived])

        with self.assertRaises(KeyError):
            self.fail(treg[int])
        with self.assertRaises(KeyError):
            self.fail(treg[int:])

        class DDA(DA):
            pass

        self.assertIs(treg[DDA:A], associations[DA])
        self.assertIs(treg[DDA:], associations[DA])
        with self.assertRaises(KeyError):
            self.fail(treg[DDA])

        for mapping in treg, associations:
            mapping[DDA] = DDA.__name__

        self.assertIs(treg[DDA:A], associations[DDA])
        self.assertIs(treg[DDA:], associations[DDA])
        self.assertIs(treg[DDA:DA], associations[DDA])
        treg.pop(DA)
        self.assertIs(treg[DA:A], associations[A])
        self.assertIs(treg[DDA:], associations[DDA])

    def test_register(self):
        treg = TypeRegistry()

        @treg.register_key(int)
        class Foo:
            pass

        self.assertIs(treg[int], Foo)

        @treg.register_value(int)
        class Bar:
            pass

        self.assertIs(treg[Bar], int)
