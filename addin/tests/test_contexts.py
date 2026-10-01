"""contexts.py — the real keypad definition passes the registry's checks."""

import unittest

import _bootstrap  # noqa: F401

from FusionKeypad.lib import contexts
from FusionKeypad.lib.registry import FusionState, Registry


class DefinitionTest(unittest.TestCase):
    def test_builds(self):
        Registry(contexts.ROOTS)  # raises on a duplicate key, a repeated context or a stray default

    def test_roots_follow_where_the_user_is(self):
        registry = Registry(contexts.ROOTS)
        cases = [
            (FusionState("FusionSolidEnvironment", editing_sketch=True, assembly=False), contexts.SKETCH),
            (FusionState("FusionSolidEnvironment", editing_sketch=True, assembly=True), contexts.SKETCH),
            (FusionState("FusionSolidEnvironment", editing_sketch=False, assembly=False), contexts.PART),
            (FusionState("FusionSolidEnvironment", editing_sketch=False, assembly=True), contexts.ASSEMBLY),
            (FusionState("CAMEnvironment", editing_sketch=False, assembly=False), None),
        ]
        for fusion, root in cases:
            with self.subTest(fusion=fusion):
                self.assertIs(registry.root_for(fusion), root)


if __name__ == "__main__":
    unittest.main()
