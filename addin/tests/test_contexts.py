"""contexts.py — the real keypad definition passes the registry's checks."""

import unittest

import _bootstrap  # noqa: F401

from lib import contexts
from lib.registry import FusionState, Registry


class DefinitionTest(unittest.TestCase):
    def test_builds(self):
        Registry(contexts.ROOTS)  # raises on a duplicate key, a repeated context or a stray default

    def test_roots_follow_where_the_user_is(self):
        registry = Registry(contexts.ROOTS)
        self.assertIs(registry.root_for(FusionState("FusionSolidEnvironment", editing_sketch=True)), contexts.SKETCH)
        self.assertIs(registry.root_for(FusionState("FusionSolidEnvironment", editing_sketch=False)), contexts.DESIGN)
        self.assertIsNone(registry.root_for(FusionState("CAMEnvironment", editing_sketch=False)))


if __name__ == "__main__":
    unittest.main()
