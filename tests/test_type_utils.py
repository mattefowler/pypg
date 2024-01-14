from unittest import TestCase

from pypg import get_submodules, find_types
from tests import test_pkg
from tests.test_pkg.module import Sentinel


class TypeDiscoveryTests(TestCase):
    def test_find_modules(self):
        results = {*get_submodules(test_pkg)}
        self.assertEqual(
            {test_pkg.module, test_pkg.subpkg.submodule, test_pkg.subpkg},
            results,
        )

    def test_find_types(self):
        results = {*find_types(Sentinel, test_pkg)}
        self.assertEqual(
            {
                test_pkg.module.Sentinel,
                test_pkg.module.Subcls,
                test_pkg.subpkg.submodule.SubmoduleTest,
            },
            results,
        )
